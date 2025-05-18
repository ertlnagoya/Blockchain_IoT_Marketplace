use sha2::Digest;

pub trait Hash {
    fn to_bytes32(&self) -> [u8; 32];
    fn to_hash(&self) -> Vec<u8>;
}

impl Hash for Vec<u8> {
    fn to_bytes32(&self) -> [u8; 32] {
        let mut data_hash = [0; 32];
        data_hash[..self.len()].copy_from_slice(self);
        data_hash
    }

    fn to_hash(&self) -> Vec<u8> {
        let mut hasher: sha2::Sha256 = sha2::Sha256::new();
        hasher.update(self);
        hasher.finalize().to_vec()
    }
}
