use reqwest::Error as ReqwestError;
use rsa::errors::Error as RsaError;
use serde_json::Error as SerdeJsonError;
use std::io;
use thiserror::Error;
use web3::Error as Web3Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("File system error: {0}")]
    FileError(#[from] io::Error),

    #[error("Ethereum client error: {0}")]
    EthereumError(#[from] Web3Error),

    #[error("RSA error: {0}")]
    RsaError(#[from] RsaError),

    #[error("HTTP request error: {0}")]
    HttpError(#[from] ReqwestError),

    #[error("JSON parse error: {0}")]
    JsonParseError(#[from] SerdeJsonError),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Invalid data: {0}")]
    InvalidData(String),

    #[error("Unexpected error: {0}")]
    Other(String),
}

pub type AppResult<T> = Result<T, AppError>;
