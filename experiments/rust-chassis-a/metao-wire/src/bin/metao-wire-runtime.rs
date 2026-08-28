use std::io::{self, BufRead, Write};
use std::thread;
use std::time::Duration;

use metao_wire::{decode_request, encode_response, WireResponse, PROTOCOL_VERSION};

fn main() {
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(line) => line,
            Err(_) => break,
        };
        let request = match decode_request(&line) {
            Ok(request) => request,
            Err(error) => {
                let _ = writeln!(
                    stdout,
                    "{{\"error\":{}}}",
                    serde_json::to_string(&error).unwrap()
                );
                let _ = stdout.flush();
                continue;
            }
        };

        if request.objective == "__hang__" {
            thread::sleep(Duration::from_secs(5));
            continue;
        }

        if request.objective == "__crash__" {
            panic!("simulated external runtime crash");
        }

        if request.objective == "__malformed_response__" {
            let _ = writeln!(stdout, "not-json");
            let _ = stdout.flush();
            continue;
        }

        if request.objective == "__bad_version__" {
            let response = WireResponse {
                protocol_version: PROTOCOL_VERSION + 1,
                execution_id: request.execution_id,
                runtime_id: "external-fake-runtime".into(),
                status: "SUCCEEDED".into(),
                result: format!("completed:{}", request.objective),
            };
            match encode_response(&response) {
                Ok(payload) => {
                    let _ = writeln!(stdout, "{payload}");
                    let _ = stdout.flush();
                }
                Err(_) => break,
            }
            continue;
        }

        let response = WireResponse {
            protocol_version: PROTOCOL_VERSION,
            execution_id: request.execution_id,
            runtime_id: "external-fake-runtime".into(),
            status: "SUCCEEDED".into(),
            result: format!("completed:{}", request.objective),
        };
        match encode_response(&response) {
            Ok(payload) => {
                let _ = writeln!(stdout, "{payload}");
                let _ = stdout.flush();
            }
            Err(_) => break,
        }
    }
}
