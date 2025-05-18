use base64::{engine::general_purpose, Engine};
use rand::{rngs::StdRng, SeedableRng};
use rsa::{traits::PublicKeyParts, BigUint, Pkcs1v15Encrypt, RsaPrivateKey, RsaPublicKey};

use crate::errors::{AppError, AppResult};

pub struct RSAKeyPair {
    pub priv_key: RsaPrivateKey,
    pub pub_key: RsaPublicKey,
}

impl RSAKeyPair {
    pub fn new() -> AppResult<Self> {
        const RSA_BITS: usize = 2048;

        let mut rng = rand::thread_rng();
        let priv_key = RsaPrivateKey::new(&mut rng, RSA_BITS).map_err(AppError::RsaError)?;
        let pub_key = RsaPublicKey::from(&priv_key);

        Ok(Self { priv_key, pub_key })
    }

    fn get_pubkey_param(&self) -> (String, String) {
        let n = BigUint::to_bytes_be(self.pub_key.n());
        let n = general_purpose::STANDARD.encode(n);
        let e = self.pub_key.e().to_string();
        (n, e)
    }

    pub fn serialize_pubkey(&self) -> String {
        serde_json::to_string(&self.get_pubkey_param()).unwrap()
    }

    pub fn with_json(json: &str) -> AppResult<Self> {
        let (n, e) =
            serde_json::from_str::<(String, String)>(json).map_err(AppError::JsonParseError)?;
        let n = general_purpose::STANDARD.decode(n.as_bytes()).unwrap();
        let n = BigUint::from_bytes_be(&n);
        let e = e.parse().unwrap();
        let pub_key = RsaPublicKey::new(n, e).map_err(AppError::RsaError)?;
        Ok(Self {
            priv_key: RsaPrivateKey::new(&mut rand::thread_rng(), 2048)
                .map_err(AppError::RsaError)?,
            pub_key,
        })
    }

    pub fn encrypt(&self, data: &str) -> String {
        let data = data.as_bytes();
        let mut rng = StdRng::from_entropy();
        let s = self
            .pub_key
            .encrypt(&mut rng, Pkcs1v15Encrypt, data)
            .unwrap();
        base64::encode(s)
    }

    pub fn decrypt(&self, data: &str) -> String {
        let data = base64::decode(data).unwrap();
        let s = self.priv_key.decrypt(Pkcs1v15Encrypt, &data).unwrap();
        String::from_utf8(s).unwrap()
    }
}
