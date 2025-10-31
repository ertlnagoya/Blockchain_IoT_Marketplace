use postgres::{Client, NoTls};
use std::process::Command;

fn check_ipfs_access() {
    // Check IPFS availability via the IPFS API version endpoint
    let output = Command::new("curl")
        .arg("-s")
        .arg("http://host.docker.internal:5001/api/v0/version")
        .arg("-X")
        .arg("POST")
        .output();

    match output {
        Ok(output) if output.status.success() => {
            println!(
                "IPFS accessible: {}",
                String::from_utf8_lossy(&output.stdout)
            );
        }
        Ok(output) => {
            eprintln!(
                "IPFS command executed but an error occurred: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        Err(e) => {
            eprintln!("Cannot access IPFS command: {}", e);
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
            println!("Content of CID:\n{}", String::from_utf8_lossy(&output.stdout));
        }
        Ok(output) => {
            eprintln!(
                "CID fetch command executed but an error occurred: {}",
                String::from_utf8_lossy(&output.stderr)
            );
        }
        Err(e) => {
            eprintln!("Cannot access CID fetch command: {}", e);
        }
    }
}

fn check_postgres_connection() {
    let mut client = match Client::connect(
        "host=host.docker.internal user=dev password=devpassword dbname=mydb",
        NoTls,
    ) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Cannot connect to PostgreSQL: {}", e);
            return;
        }
    };

    match client.simple_query("SELECT version();") {
        Ok(rows) => {
            for row in rows {
                println!("PostgreSQL version info: {:?}", row);
            }
        }
        Err(e) => {
            eprintln!("PostgreSQL query execution error: {}", e);
        }
    }
}
fn main() {
    let cid = "QmXrejoiiPLztK98sXm2ytHBLyyRJkZbxR8wX2mf5skj2j"; // Example CID
    check_ipfs_access();
    fetch_ipfs_cid_content(cid);
    check_postgres_connection();
}
