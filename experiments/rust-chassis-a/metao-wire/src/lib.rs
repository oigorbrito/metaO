use std::io::{BufRead, BufReader, Write};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RecoveryPolicy {
    pub max_recovery_attempts: u32,
    pub timeout: Duration,
}

impl RecoveryPolicy {
    pub fn new(max_recovery_attempts: u32, timeout: Duration) -> Self {
        Self {
            max_recovery_attempts,
            timeout,
        }
    }
}

impl Default for RecoveryPolicy {
    fn default() -> Self {
        Self {
            max_recovery_attempts: 1,
            timeout: Duration::from_millis(200),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuntimeExecutionFailure {
    Crash,
    Timeout,
    SpawnFailed,
    RecoveryExhausted,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuntimeExecutionBlocked {
    MalformedProtocol,
    IncompatibleProtocol,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuntimeExecutionOutcome {
    Completed {
        response: WireResponse,
        attempts: u32,
    },
    Failed {
        reason: RuntimeExecutionFailure,
        attempts: u32,
    },
    Blocked {
        reason: RuntimeExecutionBlocked,
        attempts: u32,
    },
}

fn classify_decoding_error(error: &str) -> RuntimeExecutionBlocked {
    if error.contains("unsupported protocol version") {
        RuntimeExecutionBlocked::IncompatibleProtocol
    } else {
        RuntimeExecutionBlocked::MalformedProtocol
    }
}

fn run_single_attempt(
    runtime_exe: &Path,
    request: &WireRequest,
    attempt: u32,
    timeout: Duration,
) -> RuntimeExecutionOutcome {
    let mut child = match Command::new(runtime_exe)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .env("METAO_RUNTIME_ATTEMPT", attempt.to_string())
        .spawn()
    {
        Ok(child) => child,
        Err(_) => {
            return RuntimeExecutionOutcome::Failed {
                reason: RuntimeExecutionFailure::SpawnFailed,
                attempts: attempt,
            }
        }
    };

    let payload = match encode_request(request) {
        Ok(payload) => payload,
        Err(_) => {
            let _ = child.kill();
            let _ = child.wait();
            return RuntimeExecutionOutcome::Failed {
                reason: RuntimeExecutionFailure::SpawnFailed,
                attempts: attempt,
            };
        }
    };
    if writeln!(child.stdin.as_mut().expect("child stdin"), "{payload}").is_err() {
        let _ = child.kill();
        let _ = child.wait();
        return RuntimeExecutionOutcome::Failed {
            reason: RuntimeExecutionFailure::SpawnFailed,
            attempts: attempt,
        };
    }
    child.stdin.take();

    let stdout = child.stdout.take().expect("child stdout");
    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        let mut line = String::new();
        let result = BufReader::new(stdout).read_line(&mut line).map(|_| line);
        let _ = tx.send(result);
    });

    let deadline = Instant::now() + timeout;
    loop {
        if let Ok(result) = rx.try_recv() {
            let _ = child.wait();
            return match result {
                Ok(line) if line.trim().is_empty() => RuntimeExecutionOutcome::Failed {
                    reason: RuntimeExecutionFailure::Crash,
                    attempts: attempt,
                },
                Ok(line) => match decode_response(line.trim()) {
                    Ok(response) => RuntimeExecutionOutcome::Completed {
                        response,
                        attempts: attempt,
                    },
                    Err(error) => RuntimeExecutionOutcome::Blocked {
                        reason: classify_decoding_error(&error),
                        attempts: attempt,
                    },
                },
                Err(_) => RuntimeExecutionOutcome::Failed {
                    reason: RuntimeExecutionFailure::Crash,
                    attempts: attempt,
                },
            };
        }

        if let Some(status) = child.try_wait().expect("poll child") {
            if !status.success() {
                let _ = child.wait();
                return RuntimeExecutionOutcome::Failed {
                    reason: RuntimeExecutionFailure::Crash,
                    attempts: attempt,
                };
            }
        }

        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            return RuntimeExecutionOutcome::Failed {
                reason: RuntimeExecutionFailure::Timeout,
                attempts: attempt,
            };
        }

        thread::sleep(Duration::from_millis(10));
    }
}

pub fn execute_with_recovery(
    runtime_exe: impl AsRef<Path>,
    request: &WireRequest,
    policy: RecoveryPolicy,
) -> RuntimeExecutionOutcome {
    let runtime_exe = runtime_exe.as_ref();
    let total_attempts = policy.max_recovery_attempts + 1;

    for attempt in 1..=total_attempts {
        match run_single_attempt(runtime_exe, request, attempt, policy.timeout) {
            RuntimeExecutionOutcome::Completed { response, .. } => {
                return RuntimeExecutionOutcome::Completed {
                    response,
                    attempts: attempt,
                };
            }
            RuntimeExecutionOutcome::Blocked { reason, .. } => {
                return RuntimeExecutionOutcome::Blocked {
                    reason,
                    attempts: attempt,
                };
            }
            RuntimeExecutionOutcome::Failed { reason, .. } => {
                if attempt == total_attempts {
                    return RuntimeExecutionOutcome::Failed {
                        reason: match reason {
                            RuntimeExecutionFailure::Crash
                            | RuntimeExecutionFailure::Timeout
                            | RuntimeExecutionFailure::SpawnFailed
                            | RuntimeExecutionFailure::RecoveryExhausted => {
                                RuntimeExecutionFailure::RecoveryExhausted
                            }
                        },
                        attempts: attempt,
                    };
                }
            }
        }
    }

    RuntimeExecutionOutcome::Failed {
        reason: RuntimeExecutionFailure::RecoveryExhausted,
        attempts: total_attempts,
    }
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
