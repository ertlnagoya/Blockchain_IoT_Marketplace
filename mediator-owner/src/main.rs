pub mod database;
pub mod errors;
pub mod events;
pub mod json_rsa;
pub mod metadata;
pub mod process;
pub mod service;
pub mod user;
pub mod util;

use crate::{
    database::DeployedMerchandise,
    events::{PubKeyEvent, UploadEvent},
    service::{
        ethereum::{self},
        storage::api::*,
    },
    user::EthereumUser,
    util::hash::Hash,
};
use std::str::FromStr;
use std::sync::Arc;
use std::{env, fs};
use std::process::exit;

use errors::AppResult;
use process::rule::RuleList;
use service::ethereum::eth_client::{self, DeployParam};
use web3::{
    futures::{self, StreamExt},
    types::{Address, H160, H256},
};

use notify::{
    event::{ModifyKind, RenameMode},
    EventKind, RecommendedWatcher, RecursiveMode, Watcher,
};
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::time::Duration;
use tokio::time;

use serde::Deserialize;

use std::process::Command;
use std::time::Instant;


#[derive(Debug, Deserialize)]
pub struct Config {
    pub api_url: String,
    pub rpc_url: String,
    pub eth_user_pubkey: String,
    pub eth_user_privkey: String,
    pub pubkey_contract_address: String,
    pub iot_market_contract_address: String,
    pub process_rule_file_path: String,
    pub rawdata_dir: String,
    pub camra_id: String,
    pub processed_dir: String,
    pub download_dir: String,
    pub text_file_path: String,
}

impl Config {
    pub fn from_yaml_file<P: AsRef<Path>>(path: P) -> Result<Self, Box<dyn std::error::Error>> {
        let yaml_str = fs::read_to_string(path)?;
        let config: Config = serde_yaml::from_str(&yaml_str)?;
        Ok(config)
    }
}

/// Upload a JSON file to IPFS
fn upload_json_to_ipfs<P: AsRef<Path>>(json_path: P) -> Option<String> {
    let path_str = json_path.as_ref().to_str().unwrap();

    let output = Command::new("curl")
        .arg("-s")
        .arg("-X")
        .arg("POST")
        .arg("-F")
        .arg(format!("file=@{}", path_str))
        .arg("http://host.docker.internal:5001/api/v0/add")
        .output();

    match output {
        Ok(output) if output.status.success() => {
            // Get CID from IPFS
            let v: serde_json::Value = serde_json::from_slice(&output.stdout)
                .expect("Failed to parse IPFS response");
            let cid = v.get("Hash")
                .expect("No Hash field in IPFS response")
                .as_str()
                .expect("Hash field is not a string")
                .to_string();
            Some(cid)
        }
        Ok(output) => {
            eprintln!(
                "⚠️ Upload failed: {}",
                String::from_utf8_lossy(&output.stderr)
            );
            None
        }
        Err(e) => {
            eprintln!("❌ curl command execution error: {}", e);
            None
        }
    }
}

fn upload_json_info_to_postgres<P: AsRef<Path>>(json_path: P, cid: &str) -> AppResult<()> {
    // Read the JSON file
    let json_content = std::fs::read_to_string(&json_path)
        .map_err(|e| errors::AppError::DatabaseError(format!("Failed to read JSON file: {}", e)))?;
    let json_data: serde_json::Value = serde_json::from_str(&json_content)
        .map_err(|e| errors::AppError::DatabaseError(format!("Failed to parse JSON: {}", e)))?;

    // Extract required fields
    let start_timestamp = json_data.get("start_timestamp")
        .and_then(|v| v.as_str())
        .ok_or_else(|| errors::AppError::DatabaseError("start_timestamp not found".to_string()))?;
    let end_timestamp = json_data.get("end_timestamp")
        .and_then(|v| v.as_str())
        .ok_or_else(|| errors::AppError::DatabaseError("end_timestamp not found".to_string()))?;
    let location = json_data.get("location")
        .and_then(|v| v.as_object())
        .ok_or_else(|| errors::AppError::DatabaseError("location not found".to_string()))?;
    let latitude = location.get("latitude")
        .and_then(|v| v.as_f64())
        .ok_or_else(|| errors::AppError::DatabaseError("latitude not found".to_string()))?;
    let longitude = location.get("longitude")
        .and_then(|v| v.as_f64())
        .ok_or_else(|| errors::AppError::DatabaseError("longitude not found".to_string()))?;
    let exist_people = json_data.get("exist_person")
        .and_then(|v| v.as_bool())
        .ok_or_else(|| errors::AppError::DatabaseError("exist_person not found".to_string()))?;

    // Build SQL
    let sql = format!(
        "INSERT INTO ipfs_records (cid, start_timestamp, end_timestamp, location, exist_people) \
        VALUES ('{}', '{}', '{}', ST_SetSRID(ST_MakePoint({}, {}), 4326), '{}') \
        ON CONFLICT (cid) DO NOTHING;",
        cid, start_timestamp, end_timestamp, longitude, latitude, exist_people
    );

    // Execute with psql
    let output = Command::new("psql")
        .arg("-h")
        .arg("host.docker.internal")
        .arg("-U")
        .arg("dev")
        .arg("-d")
        .arg("mydb")
        .arg("-c")
        .arg(&sql)
        .env("PGPASSWORD", "devpassword")
        .output();

    match output {
        Ok(output) if output.status.success() => {
            // println!("Inserted data into ipfs_records table");
            Ok(())
        }
        Ok(output) => {
            eprintln!(
                "⚠️ Failed to insert into PostgreSQL: {}",
                String::from_utf8_lossy(&output.stderr)
            );
            Err(errors::AppError::DatabaseError(
                "Failed to insert into PostgreSQL".to_string(),
            ))
        }
        Err(e) => {
            eprintln!("❌ PostgreSQL command execution error: {}", e);
            Err(errors::AppError::DatabaseError(
                "PostgreSQL command execution error".to_string(),
            ))
        }
    }
}


#[tokio::main]
async fn main() -> AppResult<()> {
    // Get command-line arguments
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 {
        eprintln!("Usage: {} <path to YAML file>", args[0]);
        std::process::exit(1);
    }

    let filepath = &args[1];

    // Read file
    let config = Arc::new(match Config::from_yaml_file(filepath) {
        Ok(cfg) => {
            println!("API URL: {}", cfg.api_url);
            println!("RAW DATA DIR: {}", cfg.rawdata_dir);
            cfg
        }
        Err(e) => {
            eprintln!("Failed to read config file: {}", e);
            std::process::exit(1);
        }
    });

    println!("====================");
    println!("Starting initialization");
    println!("====================");

    let rules = RuleList::new(&config.process_rule_file_path).await?;

    let deployed_files = Arc::new(DeployedMerchandise::new());

    // generate rsa key
    let rsa_keypair = Arc::new(json_rsa::RSAKeyPair::new()?);

    // storage_client
    let storage_client = StorageClient::new(&config.api_url);

    // ethereum_client
    let eth_user = EthereumUser::new(&config.eth_user_pubkey, &config.eth_user_privkey)?;
    let eth_client = Arc::new(eth_client::Ethereum::new(
        &config.rpc_url,
        eth_user.get_account(),
        eth_user.get_private_key(),
    ));

    // check service health
    storage_client.health_check().await?;
    eth_client.check_existance().await?;

    // upload pubkey to blockchain
    let pub_key_str = rsa_keypair.serialize_pubkey();
    let tx = eth_client
        .upload_pubkey(&config.pubkey_contract_address, &pub_key_str)
        .await;
    match tx {
        Ok(_) => {
            println!("Pubkey uploaded successfully");
        }
        Err(e) => {
            panic!("Error uploading pubkey, {}", e);
        }
    }

    println!("====================");
    println!("Initialization complete!");
    println!("====================\n\n");

    // file watcher thread
    println!("====================");
    println!("Starting File Watcher");
    println!("====================");

    let db = Arc::clone(&deployed_files);
    let deploy_eth_client = Arc::clone(&eth_client);
    let config_clone = Arc::clone(&config);
    let watcher_thread = tokio::spawn(async move {
        let raw_data_dir = &config_clone.rawdata_dir;
        let entries = match fs::read_dir(raw_data_dir) {
            Ok(entries) => entries,
            Err(e) => {
                eprintln!("Failed to read raw data dir: {}", e);
                return;
            }
        };

        let re = regex::Regex::new(&format!(r"^{}_movie_([0-9]+)\.json$", config_clone.camra_id)).unwrap();
        let start = Instant::now();
        let mut elapsed_times: [std::time::Duration; 10] = [Duration::from_secs(0); 10];
        for entry in entries.flatten() {
            let path = entry.path();
            if let Some(file_name) = path.file_name().and_then(|n| n.to_str()) {
                if let Some(caps) = re.captures(file_name) {
                    let mut mp4_path = path.clone();
                    mp4_path.set_extension("mp4");
                    if !mp4_path.exists() {
                        eprintln!("Corresponding mp4 file does not exist for json: {:?}", path);
                        continue;
                    }
                    // Add processing to read the JSON file here
                    let json_content = match fs::read_to_string(&path) {
                        Ok(content) => content,
                        Err(e) => {
                            eprintln!("Failed to read json file {:?}: {}", path, e);
                            continue;
                        }
                    };

                    // Deserialize JSON contents
                    let mut json_data: serde_json::Value = match serde_json::from_str(&json_content) {
                        Ok(data) => data,
                        Err(e) => {
                            eprintln!("Failed to parse json file {:?}: {}", path, e);
                            continue;
                        }
                    };
                    let exist_person = match json_data.get("person_ids") {
                        Some(ids) if ids.is_object() && !ids.as_object().unwrap().is_empty() => true,
                        _ => false,
                    };
                    json_data["exist_person"] = serde_json::Value::Bool(exist_person);
                    json_data.as_object_mut().map(|obj| obj.remove("person_ids"));
                    
                    for matched_rules in rules.iter().filter(|rule| rule.is_matched(&mp4_path)) {
                        let processer = matched_rules.parse_processer().unwrap();
                        let metadata = matched_rules.parse_metadata().unwrap();
                        let start = Instant::now();
                        let processed_file = match process::caller::call_processer(
                            mp4_path.to_str().unwrap(),
                            &config_clone.processed_dir,
                            processer,
                        )
                        .await
                        {
                            Ok(output) => output,
                            Err(e) => {
                                panic!("Error processing file: {}", e);
                            }
                        };
                        let elapsed = start.elapsed();
                        elapsed_times[0] += elapsed;
                        // Get info of the file to be deployed (file size, creation date, etc.)
                        let meta_info = metadata.create_metadata(&processed_file).unwrap();
                        let contract_info = matched_rules.get_contract();
                        let deploy_param = DeployParam::new(
                            contract_info.get_price(),
                            processed_file.clone(),
                            config_clone.pubkey_contract_address.clone(),
                            contract_info.get_permissions(),
                            meta_info,
                        )
                        .await
                        .unwrap();
                        let start = Instant::now();
                        match deploy_eth_client.deploy_product(deploy_param).await {
                            Ok(address) => {
                                deploy_eth_client
                                    .register_product(&config_clone.iot_market_contract_address, address)
                                    .await
                                    .unwrap();
                                db.insert(address, processed_file.clone()).await;
                                json_data["address"] = serde_json::Value::String(format!("{:?}", address));
                                json_data["owner"] = serde_json::Value::String(format!("{:?}", deploy_eth_client.account));
                                // println!(
                                //     "Product deployed successfully with address: {:?} for file {:?}",
                                //     address,
                                //     processed_file
                                // );
                            }
                            Err(e) => {
                                eprintln!(
                                    "Error deploying product for file {:?}: {}",
                                    processed_file, e
                                );
                                continue; // Skip if deployment fails
                            }
                        }
                        let elapsed = start.elapsed();
                        elapsed_times[1] += elapsed;
                        // Output JSON to processed_dir
                        let processed_json_path = Path::new(&config_clone.processed_dir)
                            .join(path.file_name().unwrap());
                        match fs::write(&processed_json_path, serde_json::to_string_pretty(&json_data).unwrap()) {
                            Ok(_) => {}
                            Err(e) => {
                                eprintln!("Failed to write processed JSON: {}", e);
                            }
                        }
                        
                        // Upload to IPFS
                        let start = Instant::now();
                        let cid = upload_json_to_ipfs(&processed_json_path);
                        // println!("Uploaded JSON to IPFS with CID: {:?}", cid);
                        let elapsed = start.elapsed();
                        elapsed_times[2] += elapsed;

                        // Upload to PostgreSQL
                        let start = Instant::now();
                        if let Some(cid) = cid {
                            if let Err(e) = upload_json_info_to_postgres(&processed_json_path, &cid) {
                                eprintln!("Failed to upload JSON info to PostgreSQL: {}", e);
                            } else {
                                // println!("JSON info uploaded to PostgreSQL successfully");
                            }
                        } else {
                            eprintln!("Failed to upload JSON to IPFS, skipping PostgreSQL upload");
                        }
                        let elapsed = start.elapsed();
                        elapsed_times[3] += elapsed;
                    }
                }       
            }
        }
        let elapsed = start.elapsed();
        println!("Initialization elapsed time for initialization and processing: {:.2?}", elapsed);
        println!("Elapsed times for each step:");
        println!("1. File processing: {:.2?}", elapsed_times[0]);
        println!("2. IoT Market deploy: {:.2?}", elapsed_times[1]);
        println!("3. IPFS upload: {:.2?}", elapsed_times[2]);
        println!("4. PostgreSQL upload: {:.2?}", elapsed_times[3]);
    });

    // watch blockchain
    println!("====================");
    println!("Starting blockchain watch");
    println!("====================");
    let eth_client = Arc::clone(&eth_client);
    let blockchain_thread = tokio::spawn(async move {
        let filter = eth_client.create_evnet_filter(None).await;
        let stream = filter.stream(std::time::Duration::from_secs(2));
        futures::pin_mut!(stream);
        loop {
            // Monitor logs in a loop
            let log = match stream.next().await.unwrap() {
                Ok(log) => log,
                Err(e) => {
                    panic!("Error watching blockchain, {}", e);
                }
            };
            // Use Arc (Atomic Reference Counted) to avoid excessive cloning
            let storage_client = storage_client.clone();
            let eth_client = eth_client.clone();
            let key_pair = rsa_keypair.clone();
            let deployed_files = deployed_files.clone();
            let config = config.clone();

            // Spawn a task to handle each incoming log
            tokio::spawn(async move {
                let account_address = H256::from(eth_client.account);
                let topics = log.topics.clone();
                let event = topics.first().unwrap();
                let owner = topics.get(1).unwrap();
                let buyer = topics.get(2).unwrap();
                let event_emitter = log.address;

                // On purchase event and when we are the data provider
                if owner == &account_address && event == &ethereum::topic::topic_purchase() {
                    println!("Your Product is bought by {}", buyer);
                    println!("Event emitter is ... {:?}", event_emitter);
                    let upload_file_path = deployed_files.get(&event_emitter).await.unwrap();
                    // upload file to api
                    let path = match storage_client.post_file(upload_file_path).await {
                        Ok(path) => {
                            println!("File uploaded successfully: {}", path);
                            path
                        }
                        Err(e) => {
                            panic!("Error uploading file {}", e);
                        }
                    };

                    // encrypt with pubkey
                    let pub_key = PubKeyEvent::new(&log).get_pubkey();
                    let encript_uri = match json_rsa::RSAKeyPair::with_json(&pub_key) {
                        Ok(key_pair) => key_pair.encrypt(&path),
                        Err(e) => {
                            panic!("Error encrypting file path, {}", e);
                        }
                    };
                    println!("Encrypted uri is ... {:?}", encript_uri);

                    // send event to blockchain
                    match eth_client.emit_upload(log.address, &encript_uri).await {
                        Ok(_) => {
                            println!("Upload event sent successfully");
                        }
                        Err(e) => {
                            panic!("Error sending upload event, {}", e);
                        }
                    }
                }
                if buyer == &account_address && event == &ethereum::topic::topic_purchase() {
                    println!("You bought a product of {}", owner);
                }
                // On upload event and when we are the data buyer
                if buyer == &account_address && event == &ethereum::topic::topic_upload() {
                    let access_key = UploadEvent::new(&log).get_uri();
                    println!("Encript File path is ... {:?}", access_key);
                    let access_key = key_pair.decrypt(&access_key);
                    println!("Decrypted access_key path is ... {:?}", access_key);

                    // Download file and Save it
                    println!("Downloading file...");
                    match storage_client.download_file(&access_key).await {
                        Ok(response) => {
                            let download_path = format!("{}/{}", config.download_dir.clone(), response.file_name);
                            // FIXME: Save according to file format; simple-storage needs improvement
                            tokio::fs::write(&download_path, response.file)
                                .await
                                .unwrap();
                            println!("File downloaded successfully");

                            // Verify file
                            let file = tokio::fs::read(&download_path).await.unwrap();
                            let data_hash = file.to_hash().to_bytes32();
                            let product_address = log.address;
                            let response =
                                eth_client.verify_product(product_address, data_hash).await;
                            match response {
                                Ok(result) => {
                                    println!("Verification result: {}", result);
                                }
                                Err(e) => {
                                    println!("Error verifying product, {}", e);
                                }
                            }
                        }
                        Err(e) => {
                            println!("Error downloading file {}", e);
                        }
                    }
                }
                // On verification event and when we are the data provider
                if owner == &account_address && event == &ethereum::topic::topic_verify() {
                    let result = !topics.get(3).unwrap().is_zero();
                    let contract_address = log.address;
                    // FIXME: If verification fails, re-upload the data N times
                    match result {
                        true => {
                            println!("Verification is successful");
                            match eth_client.withdraw(contract_address).await {
                                Ok(_) => {
                                    println!("Withdraw successful");
                                }
                                Err(e) => {
                                    println!("Error withdrawing, {}", e);
                                }
                            }
                        }
                        false => {
                            // Re-upload and retry
                            println!("Verification failed, retrying...");
                            // upload file to api
                            let upload_file_path =
                                deployed_files.get(&event_emitter).await.unwrap();
                            let path = match storage_client.post_file(upload_file_path).await {
                                Ok(path) => {
                                    println!("File uploaded successfully: {}", path);
                                    path
                                }
                                Err(e) => {
                                    panic!("Error uploading file {}", e);
                                }
                            };
                            // FIX: Obtain pubkey
                            let addr2 = config.pubkey_contract_address.clone();
                            let factory = Address::from_str(&addr2).unwrap();
                            let buyer: H160 = (*buyer).into();

                            let pub_key: String =
                                eth_client.get_pubkey(factory, buyer).await.unwrap();
                            // encrypt with pubkey
                            let encript_uri = match json_rsa::RSAKeyPair::with_json(&pub_key) {
                                Ok(key_pair) => key_pair.encrypt(&path),
                                Err(e) => {
                                    panic!("Error encrypting file path, {}", e);
                                }
                            };
                            println!("Encrypted uri is ... {:?}", encript_uri);
                            // send event to blockchain
                            match eth_client.emit_upload(log.address, &encript_uri).await {
                                Ok(_) => {
                                    println!("Upload event sent successfully");
                                }
                                Err(e) => {
                                    panic!("Error sending upload event, {}", e);
                                }
                            }
                        }
                    }
                }
            });
        }
    });

    // start threads
    let _ = tokio::join!(watcher_thread, blockchain_thread);
    Ok(())
}

async fn monitor_folder(path: &str) -> Option<PathBuf> {
    let (tx, rx) = mpsc::channel();

    // Create watcher and start monitoring
    let mut watcher = RecommendedWatcher::new(tx, notify::Config::default()).ok()?;
    watcher
        .watch(Path::new(path), RecursiveMode::NonRecursive)
        .ok()?;
    println!("monitor_folder created watcher. Path:{path}");

    rx.iter().flatten().find_map(|event| {
        println!("watcher's event.kind: {:?}", event.kind);
        if let EventKind::Create(notify::event::CreateKind::File) = event.kind {
            event.paths.first().cloned()
        } else if let EventKind::Modify(notify::event::ModifyKind::Name(RenameMode::To)) =
            event.kind
        {
            event.paths.first().cloned()
        } else {
            None
        }
    })
}
