use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

fn unique_name(prefix: &str) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock should be monotonic enough")
        .as_nanos();
    format!("{prefix}-{nanos}")
}

fn service_exe() -> PathBuf {
    PathBuf::from(
        env::var("CARGO_BIN_EXE_metao-testkit-service")
            .expect("service binary must be built by cargo test"),
    )
}

fn spawn_effect_service(state_path: &PathBuf) -> (Child, ChildStdin, BufReader<ChildStdout>) {
    let mut child = Command::new(service_exe())
        .arg("effect")
        .arg(state_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to start effect service");
    let stdin = child.stdin.take().expect("service stdin");
    let stdout = child.stdout.take().expect("service stdout");
    (child, stdin, BufReader::new(stdout))
}

fn send_json(
    stdin: &mut ChildStdin,
    reader: &mut BufReader<ChildStdout>,
    value: serde_json::Value,
) -> serde_json::Value {
    writeln!(stdin, "{value}").expect("service write");
    stdin.flush().expect("service flush");
    let mut line = String::new();
    reader.read_line(&mut line).expect("service read");
    serde_json::from_str(line.trim()).expect("service response")
}

#[test]
fn durable_external_effect_dedup_across_ack_loss_and_restart() {
    let root = env::temp_dir().join(unique_name("metao-effect"));
    fs::create_dir_all(&root).unwrap();
    let state_path = root.join("effect-state.json");

    let (mut child, mut stdin, mut reader) = spawn_effect_service(&state_path);

    let first = send_json(
        &mut stdin,
        &mut reader,
        serde_json::json!({
            "effect_id": "ticket-1",
            "idempotency_key": "key-1",
            "execution_id": "exec-a",
            "attempt": 1,
            "payload": "create-ticket"
        }),
    );
    assert_eq!(first["status"], "APPLIED");
    assert_eq!(first["application_count"], 1);

    let retry = send_json(
        &mut stdin,
        &mut reader,
        serde_json::json!({
            "effect_id": "ticket-1",
            "idempotency_key": "key-1",
            "execution_id": "exec-a",
            "attempt": 2,
            "payload": "create-ticket"
        }),
    );
    assert_eq!(retry["status"], "ALREADY_APPLIED");
    assert_eq!(retry["application_count"], 2);

    drop(stdin);
    let _ = child.wait();

    let (mut child2, mut stdin2, mut reader2) = spawn_effect_service(&state_path);
    let restart = send_json(
        &mut stdin2,
        &mut reader2,
        serde_json::json!({
            "effect_id": "ticket-1",
            "idempotency_key": "key-1",
            "execution_id": "exec-b",
            "attempt": 1,
            "payload": "create-ticket"
        }),
    );
    assert_eq!(restart["status"], "ALREADY_APPLIED");
    assert_eq!(restart["application_count"], 3);

    let omitted_history = send_json(
        &mut stdin2,
        &mut reader2,
        serde_json::json!({
            "effect_id": "ticket-1",
            "idempotency_key": "key-1",
            "execution_id": "exec-c",
            "attempt": 1,
            "payload": "create-ticket"
        }),
    );
    assert_eq!(omitted_history["status"], "ALREADY_APPLIED");
    assert_eq!(omitted_history["application_count"], 4);

    drop(stdin2);
    let _ = child2.wait();

    fs::remove_file(&state_path).ok();
    fs::remove_dir_all(&root).ok();
}
