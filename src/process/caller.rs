use regex::Regex;
use std::{
    io,
    path::{Path, PathBuf},
};
use tokio::process::Command;

use super::script::ScriptFile;

const SCRIPT_DIR: &str = "/workspaces/mediator/scripts/";

pub async fn call_processer(
    input_file: &str,
    output_dir: &str,
    script: ScriptFile,
) -> io::Result<PathBuf> {
    // check existence of the script, video file and output directory
    let file_path = check_script_existance(SCRIPT_DIR)?;
    {
        let input_file = Path::new(&input_file);
        if !input_file.exists() {
            return Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("File not found: {}", input_file.display()),
            ));
        }
        let output_dir = Path::new(&output_dir);
        if !output_dir.exists() {
            return Err(io::Error::new(
                io::ErrorKind::NotFound,
                format!("Output directory not found: {}", output_dir.display()),
            ));
        }
    }

    let script_file = file_path.join(script.get_script_file_name());
    let output = Command::new("python")
        .arg(script_file)
        .arg(format!("--input_video={}", input_file))
        .arg(format!("--output_dir={}", output_dir))
        .output()
        .await;

    match output {
        Ok(output) if output.status.success() => {
            let stdout = String::from_utf8(output.stdout)
                .unwrap_or_else(|_| "Failed to parse output as UTF-8".to_string());
            match extract_output_path(&stdout) {
                Some(path) => Ok(path),
                None => Err(io::Error::new(
                    io::ErrorKind::Other,
                    "Output file path not found",
                )),
            }
        }
        Ok(output) => Err(io::Error::new(
            io::ErrorKind::Other,
            format!(
                "Script execution failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ),
        )),
        Err(e) => Err(e),
    }
}

fn check_script_existance(file_path: &str) -> io::Result<&Path> {
    let script_path = Path::new(file_path);
    if !script_path.exists() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("Script file not found: {}", file_path),
        ));
    }
    Ok(script_path)
}

/// 標準出力の文字列からファイルパスを抽出し、`PathBuf` として返す関数
fn extract_output_path(stdout: &str) -> Option<PathBuf> {
    let re = Regex::new(r".*\.(mp4|jpg|txt)$").unwrap();

    stdout
        .lines()
        .rev() // 出力を逆順に確認
        .find_map(|line| {
            // 正規表現に一致する行をパスとして判定
            if re.is_match(line.trim()) {
                Some(PathBuf::from(line.trim()))
            } else {
                None
            }
        })
}
