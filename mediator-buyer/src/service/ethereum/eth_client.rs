use std::{collections::HashMap, path::PathBuf, str::FromStr};
use web3::{
    api::BaseFilter,
    contract::{Contract, Options},
    ethabi::Address,
    transports::Http,
    types::{FilterBuilder, Log, H160, H256, U256},
    Error, Web3,
};

use crate::util::hash::Hash;

pub struct Ethereum {
    pub web3: Web3<Http>,
    pub account: H160,
    pub private_key: String,
}

pub struct DeployParam {
    price: U256,
    data_hash: [u8; 32],
    pubkey_address: Address,
    access_denied_addresses: Vec<Address>, // List of denied addresses
    additional_info_keys: Vec<String>,     // Additional info keys
    additional_info_values: Vec<String>,   // Additional info values
}

impl DeployParam {
    pub async fn new(
        price: u64,
        file: PathBuf,
        pubkey_address: String,
        access_denied_addresses: Vec<String>,
        meta_info: HashMap<String, String>,
    ) -> Result<Self, web3::contract::Error> {
        // Read the file (to compute a hash that will be referenced on-chain)
        let file = match tokio::fs::read(&file).await {
            Ok(data) => data,
            Err(e) => panic!("Error reading file: {:?}", e),
        };
        let data_hash = file.to_hash().to_bytes32();

        let pub_key = Address::from_str(&pubkey_address).unwrap();
        let denied_addresses: Vec<Address> = access_denied_addresses
            .iter()
            .map(|addr| Address::from_str(addr).unwrap())
            .collect();
        let additional_info_keys = meta_info.keys().cloned().collect();
        let additional_info_values = meta_info.values().cloned().collect();
        Result::Ok(DeployParam {
            price: U256::from(price),
            data_hash,
            pubkey_address: pub_key,
            access_denied_addresses: denied_addresses,
            additional_info_keys,
            additional_info_values,
        })
    }
}

impl Ethereum {
    pub fn new(url: &str, account: &str, key: &str) -> Self {
        let transport = web3::transports::Http::new(url).unwrap();
        let web3 = web3::Web3::new(transport);
        let account = Address::from_str(account).unwrap();
        let private_key = key.to_string();
        Ethereum {
            web3,
            account,
            private_key,
        }
    }

    pub async fn check_existance(&self) -> Result<bool, Error> {
        self.web3.net().is_listening().await
    }

    pub async fn create_evnet_filter(&self, topic: Option<Vec<H256>>) -> BaseFilter<Http, Log> {
        let filter = FilterBuilder::default()
            //.address(vec![self.account])
            .topics(topic, None, None, None)
            .build();

        self.web3
            .eth_filter()
            .create_logs_filter(filter)
            .await
            .unwrap()
    }

    pub async fn upload_pubkey(
        &self,
        factory: &str,
        params: &str,
    ) -> Result<H256, web3::contract::Error> {
        let factory = Address::from_str(factory).unwrap();
        let factory =
            Contract::from_json(self.web3.eth(), factory, include_bytes!("./PubKey.json"))
                .expect("unable to get factory");
        factory
            .call(
                "registerKey",
                params.to_string(),
                self.account,
                Options::default(),
            )
            .await
    }

    pub async fn get_pubkey(
        &self,
        factory: H160,
        address: H160,
    ) -> Result<String, web3::contract::Error> {
        let contract =
            Contract::from_json(self.web3.eth(), factory, include_bytes!("./PubKey.json"))
                .expect("unable to get contract");

        let key: Result<String, web3::contract::Error> = contract
            .query("getPubKey", address, self.account, Options::default(), None)
            .await;
        key
    }

    pub async fn deploy_product(
        &self,
        deploy_param: DeployParam,
    ) -> Result<Address, web3::contract::Error> {
        let bytecode = include_str!("./Merchandise.bin").trim();

        let merchandise = Contract::deploy(self.web3.eth(), include_bytes!("./Merchandise.json"))?
            .confirmations(0) // Number of block confirmations (immediate)
            .options(Options::default()) // Options
            .execute(
                bytecode,
                (
                    deploy_param.price.to_owned(),
                    deploy_param.data_hash.to_owned(),
                    deploy_param.pubkey_address.to_owned(),
                    deploy_param.access_denied_addresses.to_owned(),
                    deploy_param.additional_info_keys.to_owned(),
                    deploy_param.additional_info_values.to_owned(),
                ),
                self.account, // Deployment account
            )
            .await?;

        Ok(merchandise.address())
    }

    pub async fn register_product(
        &self,
        iot_market: &str,
        merchandise: Address,
    ) -> Result<H256, web3::contract::Error> {
        let iot_market = Address::from_str(iot_market).unwrap();

        let iot_market = Contract::from_json(
            self.web3.eth(),
            iot_market,
            include_bytes!("./IoTMarket.json"),
        )
        .expect("unable to get factory");
        iot_market
            .call(
                "registerMerchandise",
                (merchandise,),
                self.account,
                Options::default(),
            )
            .await
    }

    pub async fn verify_product(
        &self,
        address: H160,
        data_hash: [u8; 32],
    ) -> Result<bool, web3::contract::Error> {
        let contract = Contract::from_json(
            self.web3.eth(),
            address,
            include_bytes!("./Merchandise.json"),
        )
        .expect("unable to get contract");

        let _: Result<H256, web3::contract::Error> = contract
            .call("verify", (data_hash,), self.account, Options::default())
            .await;

        // Determine success or failure by checking the state
        let state: Result<U256, web3::contract::Error> = contract
            .query("getState", (), self.account, Options::default(), None)
            .await;

        match state {
            Ok(value) => {
                if value.is_zero() {
                    Ok(true)
                } else {
                    Ok(false)
                }
            }
            Err(e) => Err(e),
        }
    }

    pub async fn withdraw(&self, address: H160) -> Result<H256, web3::contract::Error> {
        let contract = Contract::from_json(
            self.web3.eth(),
            address,
            include_bytes!("./Merchandise.json"),
        )
        .expect("unable to get contract");

        contract
            .call("withdraw", (), self.account, Options::default())
            .await
    }

    pub async fn emit_upload(
        &self,
        address: H160,
        upload_uri: &str,
    ) -> Result<H256, web3::contract::Error> {
        let contract = Contract::from_json(
            self.web3.eth(),
            address,
            include_bytes!("./Merchandise.json"),
        )
        .expect("unable to get contract");

        contract
            .call(
                "emitUpload",
                (upload_uri.to_string(),),
                self.account,
                Options::default(),
            )
            .await
    }
}
