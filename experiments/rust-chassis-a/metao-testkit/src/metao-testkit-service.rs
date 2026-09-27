use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::{self, BufRead, Write};
use std::path::PathBuf;

#[derive(Default, Serialize, Deserialize)]
struct EffectState {
    applied: BTreeMap<String, u64>,
}

#[derive(Default, Serialize, Deserialize)]
struct FenceState {
    current_execution_id: Option<String>,
    current_holder: Option<String>,
    generation: u64,
    fence: u64,
}

fn read_json_state<T: Default + for<'de> Deserialize<'de>>(path: &PathBuf) -> T {
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn write_json_state<T: Serialize>(path: &PathBuf, value: &T) {
    let encoded = serde_json::to_string_pretty(value).expect("serialize state");
    fs::write(path, encoded).expect("persist state");
}

fn handle_effect(state_path: &PathBuf, input: &Value) -> Value {
    let mut state: EffectState = read_json_state(state_path);
    let effect_id = input["effect_id"].as_str().unwrap_or_default().to_string();
    let count = {
        let count = state.applied.entry(effect_id).or_insert(0);
        *count += 1;
        *count
    };
    let already_applied = count > 1;
    write_json_state(state_path, &state);

    if input["drop_ack"].as_bool().unwrap_or(false) {
        std::process::exit(0);
    }

    if already_applied {
        json!({"status": "ALREADY_APPLIED", "application_count": count})
    } else {
        json!({"status": "APPLIED", "application_count": count})
    }
}

fn handle_fence(state_path: &PathBuf, input: &Value) -> Value {
    let mut state: FenceState = read_json_state(state_path);
    let cmd = input["cmd"].as_str().unwrap_or_default();
    let execution_id = input["execution_id"]
        .as_str()
        .unwrap_or_default()
        .to_string();
    let holder = input["holder"].as_str().unwrap_or_default().to_string();

    match cmd {
        "ACQUIRE" => {
            state.generation += 1;
            state.fence += 1;
            state.current_execution_id = Some(execution_id);
            state.current_holder = Some(holder);
            write_json_state(state_path, &state);
            json!({
                "status": "ACQUIRED",
                "generation": state.generation,
                "fence": state.fence,
                "current_holder": state.current_holder,
            })
        }
        "MUTATE" => {
            let generation = input["generation"].as_u64().unwrap_or_default();
            let fence = input["fence"].as_u64().unwrap_or_default();
            let current_holder = state.current_holder.clone().unwrap_or_default();
            let current_execution_id = state.current_execution_id.clone().unwrap_or_default();

            if Some(execution_id.clone()) == state.current_execution_id
                && Some(holder.clone()) == state.current_holder
                && generation == state.generation
                && fence == state.fence
            {
                write_json_state(state_path, &state);
                json!({
                    "status": "MUTATED",
                    "current_holder": current_holder,
                    "current_execution_id": current_execution_id,
                })
            } else {
                json!({
                    "status": "REJECTED_STALE_OWNER",
                    "current_holder": current_holder,
                    "current_execution_id": current_execution_id,
                })
            }
        }
        _ => json!({"status": "ERROR", "reason": "unknown command"}),
    }
}

fn main() {
    let mut args = env::args().skip(1);
    let mode = args.next().expect("mode required");
    let state_path = PathBuf::from(args.next().expect("state path required"));
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = line.expect("read request");
        if line.trim().is_empty() {
            continue;
        }
        let input: Value = serde_json::from_str(&line).expect("valid json request");
        let response = match mode.as_str() {
            "effect" => handle_effect(&state_path, &input),
            "fence" => handle_fence(&state_path, &input),
            _ => json!({"status": "ERROR", "reason": "unknown mode"}),
        };
        if !response.is_null() {
            writeln!(stdout, "{response}").expect("write response");
            stdout.flush().expect("flush response");
        }
    }
}
