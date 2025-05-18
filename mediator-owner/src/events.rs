use web3::{
    ethabi::{self, EventParam, ParamType, RawLog, Token},
    types::Log,
};

pub struct PubKeyEvent {
    pubkey: Token,
}

impl PubKeyEvent {
    pub fn new(log: &Log) -> Self {
        let params = vec![EventParam {
            name: "pubkey".to_string(),
            kind: ParamType::String,
            indexed: false,
        }];
        let event = ethabi::Event {
            name: "Purchase".to_string(),
            inputs: params,
            anonymous: false,
        };
        let ev_hash = event.signature();
        let res = event.parse_log(RawLog {
            topics: vec![ev_hash],
            data: log.data.0.clone(),
        });
        let pubkey = res.unwrap().params[0].value.clone();
        Self { pubkey }
    }

    pub fn get_pubkey(&self) -> String {
        self.pubkey.clone().to_string()
    }
}

pub struct UploadEvent {
    uri: Token,
}

impl UploadEvent {
    pub fn new(log: &Log) -> Self {
        let params = vec![EventParam {
            name: "uri".to_string(),
            kind: ParamType::String,
            indexed: false,
        }];
        let event = ethabi::Event {
            name: "Upload".to_string(),
            inputs: params,
            anonymous: false,
        };
        let ev_hash = event.signature();
        let res = event.parse_log(RawLog {
            topics: vec![ev_hash],
            data: log.data.0.clone(),
        });
        let uri = res.unwrap().params[0].value.clone();
        Self { uri }
    }

    pub fn get_uri(&self) -> String {
        self.uri.clone().to_string()
    }
}
