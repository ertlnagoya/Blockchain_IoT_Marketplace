use std::collections::HashMap;
use std::path::Path;

use super::entity::Metadata;
use super::fragment::{get_creation_date, get_file_format, get_file_size};

/// Generate basic metadata
pub fn create_basic_metadata<P: AsRef<Path>>(file_path: P) -> Result<Metadata, String> {
    let path = file_path.as_ref();

    if (!path.is_file()) {
        return Err(format!(
            "Specified file does not exist: {}",
            path.display()
        ));
    }

    let mut metadata: Metadata = HashMap::new();

    // Add file format
    metadata.insert("file_format".to_string(), get_file_format(path));

    // Add file size
    metadata.insert("data_size".to_string(), get_file_size(path)?);

    // Add creation date
    metadata.insert("creation_date".to_string(), get_creation_date(path)?);

    Ok(metadata)
}

// example
// Specify metadata type
// let metadata_type = MetadataType::from_str("basic");

// match metadata_type.create_metadata(file_path) {
//     Ok(metadata) => print_metadata(&metadata),
//     Err(err) => eprintln!("Error: {}", err),
// }
