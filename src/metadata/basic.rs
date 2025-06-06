use std::collections::HashMap;
use std::path::Path;

use super::entity::Metadata;
use super::fragment::{get_creation_date, get_file_format, get_file_size};

/// 基本メタデータの生成
pub fn create_basic_metadata<P: AsRef<Path>>(file_path: P) -> Result<Metadata, String> {
    let path = file_path.as_ref();

    if !path.is_file() {
        return Err(format!(
            "指定されたファイルが存在しません: {}",
            path.display()
        ));
    }

    let mut metadata: Metadata = HashMap::new();

    // ファイル形式を追加
    metadata.insert("file_format".to_string(), get_file_format(path));

    // ファイルサイズを追加
    metadata.insert("data_size".to_string(), get_file_size(path)?);

    // 作成日時を追加
    metadata.insert("creation_date".to_string(), get_creation_date(path)?);

    Ok(metadata)
}

// example
// メタデータタイプを指定
// let metadata_type = MetadataType::from_str("basic");

// match metadata_type.create_metadata(file_path) {
//     Ok(metadata) => print_metadata(&metadata),
//     Err(err) => eprintln!("エラー: {}", err),
// }
