use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct QsoClient {
    pub base_url: String,
}

#[derive(Debug, Serialize)]
struct IdentityCreateRequest<'a> {
    identity_id: &'a str,
    immutable_core: serde_json::Value,
    actor: &'a str,
    policy_version: &'a str,
}

#[derive(Debug, Deserialize)]
pub struct EventResponse {
    pub event_id: String,
    pub state_hash: String,
    pub object_uri: String,
}

impl QsoClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
        }
    }

    pub fn create_identity(
        &self,
        identity_id: &str,
        immutable_core: serde_json::Value,
        actor: &str,
        policy_version: &str,
    ) -> Result<EventResponse, String> {
        let url = format!("{}/v1/identity/create", self.base_url);
        let payload = IdentityCreateRequest {
            identity_id,
            immutable_core,
            actor,
            policy_version,
        };

        let response = ureq::post(&url)
            .send_json(serde_json::to_value(payload).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;

        response.into_json::<EventResponse>().map_err(|e| e.to_string())
    }
}
