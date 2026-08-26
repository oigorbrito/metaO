use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};

use metao_wire::{decode_request, decode_response, encode_request, WireRequest, PROTOCOL_VERSION};

#[test]
fn external_runtime_process_round_trip_preserves_execution_binding() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_metao-wire-runtime"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn external fake runtime");

    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "wire-exec-1".into(),
        mission_id: "wire-mission-1".into(),
        objective: "prove out-of-process seam".into(),
    };
    let payload = encode_request(&request).expect("encode request");
    writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}").expect("send request");
    child.stdin.take();

    let mut line = String::new();
    BufReader::new(child.stdout.take().expect("child stdout"))
        .read_line(&mut line)
        .expect("read response");
    let response = decode_response(line.trim()).expect("decode response");

    assert_eq!(response.protocol_version, PROTOCOL_VERSION);
    assert_eq!(response.execution_id, request.execution_id);
    assert_eq!(response.runtime_id, "external-fake-runtime");
    assert_eq!(response.status, "SUCCEEDED");
    assert_eq!(response.result, "completed:prove out-of-process seam");
    assert!(child.wait().expect("wait child").success());
}

#[test]
fn incompatible_protocol_version_fails_closed() {
    let payload = r#"{"protocol_version":999,"execution_id":"x","mission_id":"m","objective":"o"}"#;
    let error = decode_request(payload).expect_err("version mismatch must fail");
    assert!(error.contains("unsupported protocol version"));
}

#[test]
fn malformed_wire_message_fails_closed() {
    assert!(decode_request("not-json").is_err());
}

#[test]
fn canonical_request_encoding_is_deterministic() {
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "x".into(),
        mission_id: "m".into(),
        objective: "o".into(),
    };
    assert_eq!(encode_request(&request).unwrap(), encode_request(&request).unwrap());
}
