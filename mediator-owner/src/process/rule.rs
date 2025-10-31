use regex::Regex;
use serde::{Deserialize, Serialize};
use std::{error::Error, path::Path, str::FromStr};
use tokio::fs;

use crate::{
    errors::{AppError, AppResult},
    metadata::{self, entity::MetadataType},
};

use super::script::ScriptFile;

// Struct representing an individual rule
#[derive(Debug, Clone)]
pub struct Rule {
    target: Regex, // target is stored as a regular expression
    processer: ScriptDefinition,
    metadata: ScriptDefinition,
    contract: Contract,
}

impl Rule {
    /// Determine whether the specified file name matches the regular expression
    pub fn is_matched<P: AsRef<Path>>(&self, file_path: P) -> bool {
        file_path
            .as_ref()
            .file_name()
            .and_then(|os_str| os_str.to_str())
            .map(|file_name| self.target.is_match(file_name))
            .unwrap_or(false)
    }

    /// Parse the `processer` field into `ScriptFile`
    pub fn parse_processer(&self) -> Result<ScriptFile, &'static str> {
        ScriptFile::from_str(&self.processer.package).map_err(|_| "Invalid processer package name")
    }

    /// Parse the `metadata` field into `MetadataType`
    pub fn parse_metadata(&self) -> Result<MetadataType, &'static str> {
        metadata::entity::MetadataType::from_str(&self.metadata.package)
            .map_err(|_| "Invalid metadata package name")
    }

    pub fn get_contract(&self) -> &Contract {
        &self.contract
    }
}

// Struct before regex parsing (for serde)
#[derive(Debug, Serialize, Deserialize, Clone)]
struct RawRule {
    target: String,
    processer: ScriptDefinition,
    metadata: ScriptDefinition,
    contract: Contract,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct ScriptDefinition {
    package: String,
    args: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Contract {
    permissions: Vec<String>,
    price: u64,
    distribution_service: String,
}

impl Contract {
    pub fn get_permissions(&self) -> Vec<String> {
        self.permissions.clone()
    }
    pub fn get_price(&self) -> u64 {
        self.price
    }
    pub fn get_distribution_service(&self) -> &str {
        &self.distribution_service
    }
}

// Struct that manages the list of rules
#[derive(Debug, Clone)]
pub struct RuleList {
    rules: Vec<Rule>,
}

impl RuleList {
    /// Read a file and construct `RuleList`
    pub async fn new(file_path: &str) -> AppResult<Self> {
        let contents = fs::read_to_string(file_path).await?;
        let raw_rules: Vec<RawRule> = serde_json::from_str(&contents)?;

        // Convert to regular expressions
        let rules = raw_rules
            .into_iter()
            .map(|raw_rule| {
                Ok(Rule {
                    target: Regex::new(&raw_rule.target)
                        .map_err(|e| AppError::InvalidData(format!("Invalid regex: {}", e)))?,
                    processer: raw_rule.processer,
                    metadata: raw_rule.metadata,
                    contract: raw_rule.contract,
                })
            })
            .collect::<AppResult<Vec<_>>>()?;

        Ok(Self { rules })
    }

    /// Return an iterator over the rules
    pub fn iter(&self) -> std::slice::Iter<Rule> {
        self.rules.iter()
    }
}
