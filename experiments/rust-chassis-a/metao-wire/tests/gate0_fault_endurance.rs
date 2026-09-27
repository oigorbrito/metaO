use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use metao_wire::{decode_response, encode_request, WireRequest, PROTOCOL_VERSION};

const INJECTIONS_PER_CLASS: usize = 250;
const HANG_DEADLINE: Duration = Duration::from_millis(50);

fn spawn_runtime() -> Child {
    Command::new(env!("CARGO_BIN_EXE_metao-wire-runtime"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("spawn external fake runtime")
}

fn valid_request(execution_id: String) -> WireRequest {
    WireRequest {
        protocol_version: PROTOCOL_VERSION,
        execution_id,
        mission_id: "gate0-mission".into(),
        objective: "gate0-recovery".into(),
    }
}

fn assert_single_recovery_round_trip(iteration: usize) {
    let mut child = spawn_runtime();
    let request = valid_request(format!("recovery-{iteration}"));
    let payload = encode_request(&request).expect("encode recovery request");
    writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}")
        .expect("send recovery request");
    child.stdin.take();

    let mut line = String::new();
    BufReader::new(child.stdout.take().expect("child stdout"))
        .read_line(&mut line)
        .expect("read recovery response");
    let response = decode_response(line.trim()).expect("decode recovery response");
    assert_eq!(response.execution_id, request.execution_id);
    assert_eq!(response.status, "SUCCEEDED");
    assert!(child.wait().expect("wait recovery runtime").success());
}

#[test]
fn real_hang_is_contained_and_recovers_250_times() {
    for iteration in 0..INJECTIONS_PER_CLASS {
        let mut child = spawn_runtime();
        let request = WireRequest {
            protocol_version: PROTOCOL_VERSION,
            execution_id: format!("hang-{iteration}"),
            mission_id: "gate0-mission".into(),
            objective: "__hang__".into(),
        };
        let payload = encode_request(&request).expect("encode hanging request");
        writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}")
            .expect("send hanging request");
        child.stdin.take();

        let deadline = Instant::now() + HANG_DEADLINE;
        loop {
            if let Some(status) = child.try_wait().expect("poll hanging runtime") {
                panic!("hang injection {iteration} exited before containment deadline: {status}");
            }
            if Instant::now() >= deadline {
                child.kill().expect("kill timed-out runtime");
                let _ = child.wait();
                break;
            }
            thread::sleep(Duration::from_millis(2));
        }

        assert_single_recovery_round_trip(iteration);
    }
}

#[test]
fn malformed_and_incompatible_protocol_fail_closed_and_recover_250_times_each() {
    let mut child = spawn_runtime();
    let mut reader = BufReader::new(child.stdout.take().expect("child stdout"));

    for iteration in 0..INJECTIONS_PER_CLASS {
        writeln!(
            child.stdin.as_mut().expect("child stdin"),
            "not-json-{iteration}"
        )
        .expect("send malformed payload");
        let mut malformed_error = String::new();
        reader
            .read_line(&mut malformed_error)
            .expect("read malformed error");
        assert!(
            malformed_error.contains("\"error\""),
            "malformed payload must fail closed at iteration {iteration}: {malformed_error}"
        );

        let recovery = valid_request(format!("malformed-recovery-{iteration}"));
        writeln!(
            child.stdin.as_mut().expect("child stdin"),
            "{}",
            encode_request(&recovery).expect("encode recovery request")
        )
        .expect("send malformed recovery request");
        let mut recovery_line = String::new();
        reader
            .read_line(&mut recovery_line)
            .expect("read malformed recovery response");
        let response = decode_response(recovery_line.trim()).expect("decode recovery response");
        assert_eq!(response.execution_id, recovery.execution_id);
        assert_eq!(response.status, "SUCCEEDED");

        let incompatible = format!(
            "{{\"protocol_version\":999,\"execution_id\":\"bad-version-{iteration}\",\"mission_id\":\"gate0-mission\",\"objective\":\"gate0\"}}"
        );
        writeln!(child.stdin.as_mut().expect("child stdin"), "{incompatible}")
            .expect("send incompatible payload");
        let mut incompatible_error = String::new();
        reader
            .read_line(&mut incompatible_error)
            .expect("read incompatible error");
        assert!(
            incompatible_error.contains("unsupported protocol version"),
            "incompatible protocol must fail closed at iteration {iteration}: {incompatible_error}"
        );

        let recovery = valid_request(format!("version-recovery-{iteration}"));
        writeln!(
            child.stdin.as_mut().expect("child stdin"),
            "{}",
            encode_request(&recovery).expect("encode recovery request")
        )
        .expect("send version recovery request");
        let mut recovery_line = String::new();
        reader
            .read_line(&mut recovery_line)
            .expect("read version recovery response");
        let response =
            decode_response(recovery_line.trim()).expect("decode version recovery response");
        assert_eq!(response.execution_id, recovery.execution_id);
        assert_eq!(response.status, "SUCCEEDED");
    }

    child.stdin.take();
    assert!(child.wait().expect("wait external runtime").success());
}
