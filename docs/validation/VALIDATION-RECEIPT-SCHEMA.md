# Validation Receipt Schema

A validation receipt is evidence of one attempted command execution.

Required fields:
- receipt_version
- commit_sha
- command
- started_at
- finished_at
- exit_code
- test_count
- environment
- stdout
- stderr

States:
- PASS_EXECUTED: command started and exit_code is 0.
- FAIL_EXECUTED: command started and exit_code is non-zero.
- BLOCKED_ENVIRONMENT: command could not start because the environment was unavailable.
- NOT_EXECUTED: no receipt exists.

Receipts must never contain credentials or authorization headers.
