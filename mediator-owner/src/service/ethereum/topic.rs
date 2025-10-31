use std::vec;

use hex_literal::hex;
use web3::types::H256;

/** topic.rs
 *  Define blockchain topics.
 *  A topic is the keccak256 hash of an event signature.
 *  https://emn178.github.io/online-tools/keccak_256.html
 */

pub fn topic_hello() -> Option<Vec<H256>> {
    Some(vec![hex!(
        "d282f389399565f3671145f5916e51652b60eee8e5c759293a2f5771b8ddfd2e"
    )
    // "Hello(address)"
    .into()])
}

pub fn topic_purchase() -> H256 {
    // Purchase(address,address,string)
    hex!("2a012512d0f77edfcb4c5930b8b0b128a7e43ca3419186882058eb3f05706046").into()
}

pub fn topic_verify() -> H256 {
    // Verify(address,address,bool)
    hex!("d097ce000053ce97ab91fd27d014f308bce1dcc28e97bb7956720989aa0f2510").into()
}

pub fn topic_upload() -> H256 {
    // Upload(address,address,string)
    hex!("05f287e30d29b97a5ad15563cbd028af0e0178d4f5a32ff285a815e4bf5c6326").into()
}
