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

#[tokio::main]
async fn main() -> AppResult<()> {
    // コマンドライン引数を取得
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 {
        eprintln!("使い方: {} <YAMLファイルのパス>", args[0]);
        std::process::exit(1);
    }

    let filepath = &args[1];

    // ファイル読み込み
    let config = Arc::new(match Config::from_yaml_file(filepath) {
        Ok(cfg) => {
            println!("API URL: {}", cfg.api_url);
            println!("RAW DATA DIR: {}", cfg.rawdata_dir);
            cfg
        }
        Err(e) => {
            eprintln!("設定ファイル読み込みエラー: {}", e);
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
                    // ここでjsonファイルを読み込む処理を追加
                    let json_content = match fs::read_to_string(&path) {
                        Ok(content) => content,
                        Err(e) => {
                            eprintln!("Failed to read json file {:?}: {}", path, e);
                            continue;
                        }
                    };

                    // JSONの内容をデシリアライズ
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
                        // デプロイするファイルの情報を取得（ファイルサイズや作成日時など）
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
                        match deploy_eth_client.deploy_product(deploy_param).await {
                            Ok(address) => {
                                deploy_eth_client
                                    .register_product(&config_clone.iot_market_contract_address, address)
                                    .await
                                    .unwrap();
                                db.insert(address, processed_file.clone()).await;
                                json_data["address"] = serde_json::Value::String(format!("{:?}", address));
                                json_data["owner"] = serde_json::Value::String(format!("{:?}", deploy_eth_client.account));
                                println!(
                                    "Product deployed successfully with address: {:?} for file {:?}",
                                    address,
                                    processed_file
                                );
                            }
                            Err(e) => {
                                eprintln!(
                                    "Error deploying product for file {:?}: {}",
                                    processed_file, e
                                );
                                continue; // Skip if deployment fails
                            }
                        }
                        // JSONをprocessed_dirに出力
                        let processed_json_path = Path::new(&config_clone.processed_dir)
                            .join(path.file_name().unwrap());
                        match fs::write(&processed_json_path, serde_json::to_string_pretty(&json_data).unwrap()) {
                            Ok(_) => {}
                            Err(e) => {
                                eprintln!("Failed to write processed JSON: {}", e);
                            }
                        }
                    }
                }       
            }
        }
        println!("File watcher initialized for directory: {}", raw_data_dir);
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
            // loopでログを監視
            let log = match stream.next().await.unwrap() {
                Ok(log) => log,
                Err(e) => {
                    panic!("Error watching blockchain, {}", e);
                }
            };
            // Atomic Reference Counted を使ってクローンを抑制
            let storage_client = storage_client.clone();
            let eth_client = eth_client.clone();
            let key_pair = rsa_keypair.clone();
            let deployed_files = deployed_files.clone();
            let config = config.clone();

            // ログが来たらスレッドを立てて処理
            tokio::spawn(async move {
                let account_address = H256::from(eth_client.account);
                let topics = log.topics.clone();
                let event = topics.first().unwrap();
                let owner = topics.get(1).unwrap();
                let buyer = topics.get(2).unwrap();
                let event_emitter = log.address;

                // 購入処理発生 & 自身がデータ提供者の場合
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
                // Upload処理発生 & 自身がデータ購入者の場合
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
                            // FIXME: ファイル形式に合わせて保存, simple-storageの改修が必要
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
                //　検証処理発生 & 自信がデータ提供者の場合
                if owner == &account_address && event == &ethereum::topic::topic_verify() {
                    let result = !topics.get(3).unwrap().is_zero();
                    let contract_address = log.address;
                    // FIXME: 検証に失敗したら、データの再アップロードをN回行う
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
                            // 再アップロードして繰り返す
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
                            // FIX: pubkeyの取得
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

    // Watcher を作成して監視を開始
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
