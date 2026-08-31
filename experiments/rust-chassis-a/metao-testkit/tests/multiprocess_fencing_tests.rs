use std::process::{Command, Stdio};
use std::env;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::fs;

#[test]
fn test_multiprocess_fencing_and_stale_owner_rejection() {
    let test_db_path = "fencing_test.db";
    let _ = fs::remove_file(test_db_path);

    let py_script = r#"
import sys
import sqlite3
import json

db_path = sys.argv[1]
conn = sqlite3.connect(db_path, isolation_level=None)
conn.execute("CREATE TABLE IF NOT EXISTS lease (execution_id TEXT PRIMARY KEY, holder TEXT, generation INTEGER, fence INTEGER)")

def acquire(execution_id, holder):
    cur = conn.cursor()
    cur.execute("BEGIN EXCLUSIVE")
    cur.execute("SELECT generation, fence, holder FROM lease WHERE execution_id = ?", (execution_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO lease (execution_id, holder, generation, fence) VALUES (?, ?, 1, 1)", (execution_id, holder))
        cur.execute("COMMIT")
        return {"status": "ACQUIRED", "generation": 1, "fence": 1}
    else:
        gen, fence, current_holder = row
        # Takeover always increments generation
        new_gen = gen + 1
        new_fence = fence + 1
        cur.execute("UPDATE lease SET holder = ?, generation = ?, fence = ? WHERE execution_id = ?", (holder, new_gen, new_fence, execution_id))
        cur.execute("COMMIT")
        return {"status": "ACQUIRED", "generation": new_gen, "fence": new_fence}

def mutate(execution_id, holder, generation, fence):
    cur = conn.cursor()
    cur.execute("BEGIN EXCLUSIVE")
    cur.execute("SELECT holder, generation, fence FROM lease WHERE execution_id = ?", (execution_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute("ROLLBACK")
        return {"status": "ERROR"}
    current_holder, current_gen, current_fence = row
    if current_gen != generation or current_fence != fence:
        cur.execute("ROLLBACK")
        return {"status": "REJECTED_STALE_OWNER"}
    
    # mutation logic here
    cur.execute("COMMIT")
    return {"status": "MUTATED"}

for line in sys.stdin:
    req = json.loads(line)
    cmd = req['cmd']
    execution_id = req['execution_id']
    holder = req['holder']
    
    if cmd == 'ACQUIRE':
        res = acquire(execution_id, holder)
        print(json.dumps(res), flush=True)
    elif cmd == 'MUTATE':
        generation = req['generation']
        fence = req['fence']
        res = mutate(execution_id, holder, generation, fence)
        print(json.dumps(res), flush=True)
"#;

    let script_path = "fencing_mock.py";
    fs::write(script_path, py_script).unwrap();

    let spawn_proc = || {
        Command::new("python")
            .arg(script_path)
            .arg(test_db_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .expect("Failed to start python process")
    };

    let mut process_a = spawn_proc();
    let mut stdin_a = process_a.stdin.take().unwrap();
    let stdout_a = process_a.stdout.take().unwrap();
    let mut reader_a = BufReader::new(stdout_a);

    let mut process_b = spawn_proc();
    let mut stdin_b = process_b.stdin.take().unwrap();
    let stdout_b = process_b.stdout.take().unwrap();
    let mut reader_b = BufReader::new(stdout_b);

    let exec_id = "exec-123";

    // Process A acquires lease
    writeln!(stdin_a, r#"{{"cmd": "ACQUIRE", "execution_id": "{}", "holder": "A"}}"#, exec_id).unwrap();
    let mut res_a = String::new();
    reader_a.read_line(&mut res_a).unwrap();
    assert!(res_a.contains("ACQUIRED"));
    assert!(res_a.contains("\"generation\": 1"));

    // Process B fails over / takes over
    writeln!(stdin_b, r#"{{"cmd": "ACQUIRE", "execution_id": "{}", "holder": "B"}}"#, exec_id).unwrap();
    let mut res_b = String::new();
    reader_b.read_line(&mut res_b).unwrap();
    assert!(res_b.contains("ACQUIRED"));
    assert!(res_b.contains("\"generation\": 2"));

    // Process A tries to mutate with stale generation 1
    writeln!(stdin_a, r#"{{"cmd": "MUTATE", "execution_id": "{}", "holder": "A", "generation": 1, "fence": 1}}"#, exec_id).unwrap();
    let mut res_a_mutate = String::new();
    reader_a.read_line(&mut res_a_mutate).unwrap();
    assert!(res_a_mutate.contains("REJECTED_STALE_OWNER"));

    // Process B mutates with current generation 2
    writeln!(stdin_b, r#"{{"cmd": "MUTATE", "execution_id": "{}", "holder": "B", "generation": 2, "fence": 2}}"#, exec_id).unwrap();
    let mut res_b_mutate = String::new();
    reader_b.read_line(&mut res_b_mutate).unwrap();
    assert!(res_b_mutate.contains("MUTATED"));

    drop(stdin_a);
    drop(stdin_b);
    let _ = process_a.wait();
    let _ = process_b.wait();
    
    let _ = fs::remove_file(test_db_path);
    let _ = fs::remove_file(script_path);
}
