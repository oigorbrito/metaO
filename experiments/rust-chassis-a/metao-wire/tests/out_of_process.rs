use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use metao_wire::{decode_request, decode_response, encode_request, WireRequest, PROTOCOL_VERSION};

fn spawn_runtime() -> std::process::Child {
    Command::new(env!("CARGO_BIN_EXE_metao-wire-runtime"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn external fake runtime")
}

fn send_request(child: &mut std::process::Child, request: &WireRequest) {
    let payload = encode_request(request).expect("encode request");
    writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}").expect("send request");
    child.stdin.take();
}

fn read_response_line(child: &mut std::process::Child) -> String {
    let mut line = String::new();
    BufReader::new(child.stdout.take().expect("child stdout"))
        .read_line(&mut line)
        .expect("read response");
    line
}

#[test]
fn external_runtime_process_round_trip_preserves_execution_binding() {
    let mut child = spawn_runtime();
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "wire-exec-1".into(),
        mission_id: "wire-mission-1".into(),
        objective: "prove out-of-process seam".into(),
    };
    send_request(&mut child, &request);
    let line = read_response_line(&mut child);
    let response = decode_response(line.trim()).expect("decode response");

    assert_eq!(response.protocol_version, PROTOCOL_VERSION);
    assert_eq!(response.execution_id, request.execution_id);
    assert_eq!(response.runtime_id, "external-fake-runtime");
    assert_eq!(response.status, "SUCCEEDED");
    assert_eq!(response.result, "completed:prove out-of-process seam");
    assert!(child.wait().expect("wait child").success());
}

#[test]
fn hanging_external_runtime_can_be_contained_by_process_boundary() {
    let mut child = spawn_runtime();
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "wire-timeout-1".into(),
        mission_id: "wire-timeout-mission".into(),
        objective: "__hang__".into(),
    };
    send_request(&mut child, &request);

    let deadline = Instant::now() + Duration::from_millis(200);
    loop {
        if let Some(status) = child.try_wait().expect("poll child") {
            panic!("hanging fixture exited unexpectedly before timeout: {status}");
        }
        if Instant::now() >= deadline {
            child.kill().expect("kill timed-out runtime");
            let _ = child.wait();
            break;
        }
        thread::sleep(Duration::from_millis(10));
    }
}

#[test]
fn malformed_request_is_rejected_at_the_boundary() {
    let mut child = spawn_runtime();
    writeln!(child.stdin.as_mut().expect("child stdin"), "not-json").expect("send malformed");
    child.stdin.take();

    let line = read_response_line(&mut child);
    assert!(line.contains("\"error\""));
    assert!(child.wait().expect("wait malformed child").success());
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
fn malformed_response_is_rejected_at_the_boundary() {
    let mut child = spawn_runtime();
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "bad-response-1".into(),
        mission_id: "m".into(),
        objective: "__malformed_response__".into(),
    };
    send_request(&mut child, &request);

    let line = read_response_line(&mut child);
    assert!(decode_response(line.trim()).is_err());
    assert!(child
        .wait()
        .expect("wait malformed response child")
        .success());
}

#[test]
fn incompatible_protocol_version_is_rejected_at_the_boundary() {
    let mut child = spawn_runtime();
    let payload = format!(
        r#"{{"protocol_version":{},"execution_id":"x","mission_id":"m","objective":"o"}}"#,
        PROTOCOL_VERSION + 1
    );
    writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}")
        .expect("send incompatible request");
    child.stdin.take();

    let line = read_response_line(&mut child);
    assert!(line.contains("unsupported protocol version"));
    assert!(child.wait().expect("wait incompatible child").success());
}

#[test]
fn crashed_runtime_is_contained_by_the_boundary() {
    let mut child = spawn_runtime();
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "crash-1".into(),
        mission_id: "m".into(),
        objective: "__crash__".into(),
    };
    send_request(&mut child, &request);

    let line = read_response_line(&mut child);
    assert!(line.is_empty());
    let status = child.wait().expect("wait crashed child");
    assert!(!status.success());
}

#[test]
fn canonical_request_encoding_is_deterministic() {
    let request = WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id: "x".into(),
        mission_id: "m".into(),
        objective: "o".into(),
    };
    assert_eq!(
        encode_request(&request).unwrap(),
        encode_request(&request).unwrap()
    );
}
