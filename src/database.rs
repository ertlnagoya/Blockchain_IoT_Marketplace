use std::collections::HashMap;
use std::{path::PathBuf, sync::Arc};

use tokio::sync::RwLock;
use web3::types::H160;

#[derive(Clone, Debug)]
pub struct DeployedMerchandise {
    db: Arc<RwLock<HashMap<H160, PathBuf>>>,
}

impl DeployedMerchandise {
    pub fn new() -> Self {
        Self {
            db: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// データを非同期で追加
    pub async fn insert(&self, key: H160, value: PathBuf) {
        let mut db = self.db.write().await;
        db.insert(key, value);
    }

    /// データを非同期で取得
    pub async fn get(&self, key: &H160) -> Option<PathBuf> {
        let db = self.db.read().await;
        db.get(key).cloned()
    }

    /// データの一覧を非同期で表示
    pub async fn display_all(&self) {
        let db = self.db.read().await;
        println!("Deployed Merchandise DB:");
        for (key, value) in db.iter() {
            println!("Key: {:?}, Value: {:?}", key, value);
        }
    }
}

impl Default for DeployedMerchandise {
    fn default() -> Self {
        Self::new()
    }
}
