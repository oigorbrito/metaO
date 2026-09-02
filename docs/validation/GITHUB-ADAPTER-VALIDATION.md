# GitHub Adapter Validation Protocol

## Status
This protocol distinguishes execution evidence from structural inspection and hosted-CI infrastructure failures.

## Commands
```bash
python -m unittest discover -s tests/unit -p 'test_github_adapter*.py' -v
```

## Required receipt
Record:
- exact commit SHA
- Python version
- command
- exit code
- stdout/stderr
- test count
- environment identifier

## Evidence states
- PASS_EXECUTED: command completed with exit code 0.
- FAIL_EXECUTED: command completed with non-zero exit code.
- BLOCKED_ENVIRONMENT: execution environment prevented command start.
- NOT_EXECUTED: no command receipt exists.

Structural inspection is never substituted for PASS_EXECUTED.

## Cost benchmark gate
Agent vs metaO vs hybrid comparisons may begin only after at least one PASS_EXECUTED receipt exists for the adapter baseline.
