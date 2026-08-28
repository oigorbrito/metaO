use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION: u32 = 1;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WireRequest {
    pub protocol_version: u32,
    pub execution_id: String,
    pub mission_id: String,
    pub objective: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WireResponse {
    pub protocol_version: u32,
    pub execution_id: String,
    pub runtime_id: String,
    pub status: String,
    pub result: String,
}

pub fn encode_request(request: &WireRequest) -> Result<String, String> {
    serde_json::to_string(request).map_err(|error| error.to_string())
}

pub fn decode_request(payload: &str) -> Result<WireRequest, String> {
    let request: WireRequest = serde_json::from_str(payload).map_err(|error| error.to_string())?;
    if request.protocol_version != PROTOCOL_VERSION {
        return Err(format!(
            "unsupported protocol version: {}",
            request.protocol_version
        ));
    }
    Ok(request)
}

pub fn encode_response(response: &WireResponse) -> Result<String, String> {
    serde_json::to_string(response).map_err(|error| error.to_string())
}

pub fn decode_response(payload: &str) -> Result<WireResponse, String> {
    let response: WireResponse =
        serde_json::from_str(payload).map_err(|error| error.to_string())?;
    if response.protocol_version != PROTOCOL_VERSION {
        return Err(format!(
            "unsupported protocol version: {}",
            response.protocol_version
        ));
    }
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::{decode_request, decode_response, PROTOCOL_VERSION};

    #[test]
    fn malformed_request_fails_closed_through_real_decoder() {
        assert!(decode_request("{not-json").is_err());
    }

    #[test]
    fn malformed_response_fails_closed_through_real_decoder() {
        assert!(decode_response("{not-json").is_err());
    }

    #[test]
    fn unknown_request_protocol_version_fails_closed() {
        let payload = format!(
            r#"{{"protocol_version":{},"execution_id":"x1","mission_id":"m1","objective":"test"}}"#,
            PROTOCOL_VERSION + 1
        );
        let error = decode_request(&payload).expect_err("unknown version must be rejected");
        assert!(error.contains("unsupported protocol version"));
    }

    #[test]
    fn unknown_response_protocol_version_fails_closed() {
        let payload = format!(
            r#"{{"protocol_version":{},"execution_id":"x1","runtime_id":"orch-a","status":"Succeeded","result":"ok"}}"#,
            PROTOCOL_VERSION + 1
        );
        let error = decode_response(&payload).expect_err("unknown version must be rejected");
        assert!(error.contains("unsupported protocol version"));
    }
}
