use std::path::Path;

use reqwest::{multipart::Part, Client, Error, Response};

#[derive(serde::Deserialize)]
pub struct ResJson {
    upload_path: String,
}

pub struct DownloadResponse {
    pub file_name: String,
    pub file: Vec<u8>,
}

#[derive(Clone)]
pub struct StorageClient {
    client: Client,
    base_url: String,
}

impl StorageClient {
    pub fn new(base_url: &str) -> Self {
        let client = Client::new();
        Self {
            client,
            base_url: base_url.to_string(),
        }
    }

    pub async fn health_check(&self) -> Result<Response, Error> {
        let url = format!("{}/", self.base_url);
        self.client.get(url).send().await
    }

    pub async fn post_file<P>(&self, file_path: P) -> Result<String, Error>
    where
        P: AsRef<Path>,
    {
        let url = format!("{}/upload", self.base_url);
        let file = tokio::fs::read(file_path.as_ref()).await.unwrap();

        // Create multipart::Form using Part
        let file_name = file_path
            .as_ref()
            .file_name()
            .unwrap()
            .to_string_lossy()
            .to_string();
        let part = Part::bytes(file).file_name(file_name);
        let form = reqwest::multipart::Form::new().part("file", part);

        let res = self.client.post(&url).multipart(form).send().await?;
        // FIXME: Error handling needed here
        let res = res.json::<ResJson>().await?;
        Ok(res.upload_path)
    }

    pub async fn download_file(&self, access_key: &str) -> Result<DownloadResponse, Error> {
        let url = format!("{}/download?key={}", self.base_url, access_key);
        let response = match self.client.get(url).send().await {
            Ok(response) => response,
            Err(e) => return Err(e),
        };
        let file_name = response.headers().get("content-disposition").unwrap();
        let file_name = file_name.to_str().unwrap().split('=').last().unwrap();

        Ok(DownloadResponse {
            file_name: file_name.to_string(),
            file: response.bytes().await.unwrap().to_vec(),
        })
    }
}
