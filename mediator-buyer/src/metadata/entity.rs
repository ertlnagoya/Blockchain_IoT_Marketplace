use std::{collections::HashMap, path::Path, str::FromStr};

use super::basic::create_basic_metadata;

pub type Metadata = HashMap<String, String>;

#[derive(Debug)]
pub enum MetadataType {
    Basic,
}

impl MetadataType {
    /// Call the metadata function (generic)
    pub fn create_metadata<P: AsRef<Path>>(&self, file_path: P) -> Result<Metadata, String> {
        match self {
            MetadataType::Basic => create_basic_metadata(file_path),
        }
    }
}

impl FromStr for MetadataType {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "Basic" => Ok(MetadataType::Basic),
            _ => unimplemented!("Invalid metadata type: {}", s),
        }
    }
}
