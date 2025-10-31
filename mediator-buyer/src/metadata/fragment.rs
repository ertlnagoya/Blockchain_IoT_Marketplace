use chrono::{DateTime, Local};
use std::fs;
use std::path::Path;

pub fn get_file_format(path: &Path) -> String {
    path.extension()
        .map(|ext| ext.to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string())
}

pub fn get_file_size(path: &Path) -> Result<String, String> {
    fs::metadata(path)
        .map(|metadata| metadata.len().to_string())
        .map_err(|_| format!("Failed to get file size: {}", path.display()))
}

pub fn get_creation_date(path: &Path) -> Result<String, String> {
    fs::metadata(path)
        .and_then(|metadata| {
            metadata
                .created()
                .or_else(|_| metadata.modified())
                .map(|time| {
                    let datetime: DateTime<Local> = time.into();
                    datetime.format("%Y-%m-%d %H:%M:%S").to_string()
                })
        })
        .map_err(|_| format!("Failed to get creation date: {}", path.display()))
}
