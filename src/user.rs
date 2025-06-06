// owner(deployer) account
// Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
// Private Key: 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
// buyer account
// Account #2: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC (10000 ETH)
// Private Key: 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a

use crate::errors::{AppError, AppResult};

pub struct EthereumUser {
    account: String,
    private_key: String,
}

impl EthereumUser {
    pub fn new(account: &str, private_key: &str) -> AppResult<Self> {
        if !account.starts_with("0x") || account.len() != 42 {
            return Err(AppError::InvalidData(
                "Account must start with '0x' and be 42 characters long".to_string(),
            ));
        }

        if !private_key.starts_with("0x") || private_key.len() != 66 {
            return Err(AppError::InvalidData(
                "Private key must start with '0x' and be 66 characters long".to_string(),
            ));
        }

        Ok(Self {
            account: account.to_string(),
            private_key: private_key.to_string(),
        })
    }

    pub fn get_account(&self) -> &str {
        &self.account
    }

    pub fn get_private_key(&self) -> &str {
        &self.private_key
    }
}
