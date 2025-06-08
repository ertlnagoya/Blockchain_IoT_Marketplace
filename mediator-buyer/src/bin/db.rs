use postgres::{Client, NoTls};
use std::process::Command;

fn check_ipfs_access() {
    // "ipfs --version" コマンドでIPFSがインストールされているか確認
    let output = Command::new("curl")
        .arg("-s")
        .arg("http://host.docker.internal:5001/api/v0/version")
        .arg("-X")
        .arg("POST")
        .output();

    match output {
        Ok(output) if output.status.success() => {
            println!(
                "IPFSにアクセスできます: {}",
                String::from_utf8_lossy(&output.stdout)
            );
        }
        Ok(output) => {
            eprintln!(
                "IPFSコマンドは実行されましたが、エラーが発生しました: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        Err(e) => {
            eprintln!("IPFSコマンドにアクセスできません: {}", e);
        }
    }
}
fn fetch_ipfs_cid_content(cid: &str) {
    let output = Command::new("curl")
        .arg("-s")
        .arg("http://host.docker.internal:5001/api/v0/cat")
        .arg("-X")
        .arg("POST")
        .arg("-F")
        .arg(format!("arg={}", cid))
        .output();

    match output {
        Ok(output) if output.status.success() => {
            println!("CIDの内容:\n{}", String::from_utf8_lossy(&output.stdout));
        }
        Ok(output) => {
            eprintln!(
                "CID取得コマンドは実行されましたが、エラーが発生しました: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        Err(e) => {
            eprintln!("CID取得コマンドにアクセスできません: {}", e);
        }
    }
}

fn main() {
    let cid = "QmXrejoiiPLztK98sXm2ytHBLyyRJkZbxR8wX2mf5skj2j"; // 例としてCIDを指定
    check_ipfs_access();
    fetch_ipfs_cid_content(cid);

    let mut client = match Client::connect(
        "host=host.docker.internal user=dev password=devpassword dbname=mydb",
        NoTls,
    ) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("PostgreSQLに接続できません: {}", e);
            return;
        }
    };

    match client.simple_query("SELECT version();") {
        Ok(rows) => {
            for row in rows {
                println!("PostgreSQLバージョン情報: {:?}", row);
            }
        }
        Err(e) => {
            eprintln!("PostgreSQLクエリ実行エラー: {}", e);
        }
    }
}
