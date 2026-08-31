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

fn spawn_fence_service(state_path: &PathBuf) -> (Child, ChildStdin, BufReader<ChildStdout>) {
    let mut child = Command::new(service_exe())
        .arg("fence")
        .arg(state_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("failed to start fence service");
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
fn multiprocess_fencing_rejects_stale_owner_and_stale_done() {
    let root = env::temp_dir().join(unique_name("metao-fence"));
    fs::create_dir_all(&root).unwrap();
    let state_path = root.join("lease-state.json");

    let (mut process_a, mut stdin_a, mut reader_a) = spawn_fence_service(&state_path);
    let (mut process_b, mut stdin_b, mut reader_b) = spawn_fence_service(&state_path);

    let acquired_a = send_json(
        &mut stdin_a,
        &mut reader_a,
        serde_json::json!({
            "cmd": "ACQUIRE",
            "execution_id": "exec-123",
            "holder": "A"
        }),
    );
    assert_eq!(acquired_a["status"], "ACQUIRED");
    assert_eq!(acquired_a["generation"], 1);
    assert_eq!(acquired_a["fence"], 1);

    let acquired_b = send_json(
        &mut stdin_b,
        &mut reader_b,
        serde_json::json!({
            "cmd": "ACQUIRE",
            "execution_id": "exec-123",
            "holder": "B"
        }),
    );
    assert_eq!(acquired_b["status"], "ACQUIRED");
    assert_eq!(acquired_b["generation"], 2);
    assert_eq!(acquired_b["fence"], 2);

    let stale_done = send_json(
        &mut stdin_a,
        &mut reader_a,
        serde_json::json!({
            "cmd": "MUTATE",
            "execution_id": "exec-123",
            "holder": "A",
            "generation": 1,
            "fence": 1
        }),
    );
    assert_eq!(stale_done["status"], "REJECTED_STALE_OWNER");
    assert_eq!(stale_done["current_holder"], "B");

    let current_done = send_json(
        &mut stdin_b,
        &mut reader_b,
        serde_json::json!({
            "cmd": "MUTATE",
            "execution_id": "exec-123",
            "holder": "B",
            "generation": 2,
            "fence": 2
        }),
    );
    assert_eq!(current_done["status"], "MUTATED");
    assert_eq!(current_done["current_holder"], "B");

    drop(stdin_a);
    drop(stdin_b);
    let _ = process_a.wait();
    let _ = process_b.wait();

    let (mut process_c, mut stdin_c, mut reader_c) = spawn_fence_service(&state_path);
    let reacquire = send_json(
        &mut stdin_c,
        &mut reader_c,
        serde_json::json!({
            "cmd": "ACQUIRE",
            "execution_id": "exec-123",
            "holder": "C"
        }),
    );
    assert_eq!(reacquire["status"], "ACQUIRED");
    assert_eq!(reacquire["generation"], 3);
    assert_eq!(reacquire["fence"], 3);

    let stale_snapshot = send_json(
        &mut stdin_c,
        &mut reader_c,
        serde_json::json!({
            "cmd": "MUTATE",
            "execution_id": "exec-123",
            "holder": "A",
            "generation": 1,
            "fence": 1
        }),
    );
    assert_eq!(stale_snapshot["status"], "REJECTED_STALE_OWNER");
    assert_eq!(stale_snapshot["current_holder"], "C");

    drop(stdin_c);
    let _ = process_c.wait();

    fs::remove_file(&state_path).ok();
    fs::remove_dir_all(&root).ok();
}
