# Release Evidence Validator

Status: PREPARED AS INDEPENDENT RELEASE-HARNESS TOOLING.

## Purpose

The local release gate writes machine-readable JSON, but release authority must not depend on manually reading a console summary or trusting only the top-level `overall` field.

This validator provides a separate fail-closed check for release evidence produced by `scripts/run-local-release-gate.ps1`.

It does **not** execute the metaO functional gates and it cannot turn a failed or incomplete run into PASS. It only validates already-produced evidence.

## Architecture boundary

This is release harness tooling only.

```text
src/metao/** changed = NO
OrchestratorContract changed = NO
runtime behavior changed = NO
```

The validator lives in:

```text
scripts/validate_release_evidence.py
```

and uses only the Python standard library.

## Fail-closed checks

A JSON file is accepted as `VALID_PASS` only when all of the following are true:

1. `schema_version == 1`;
2. `generated_at_utc` is an offset-aware ISO-8601 timestamp;
3. branch exactly matches the expected branch supplied to the validator;
4. commit exactly matches the expected candidate SHA supplied to the validator;
5. `clean_worktree == true`;
6. Python version is `3.12.x`;
7. runtime pins exactly match:
   - OpenAI Agents `0.20.0`;
   - CrewAI `1.15.16`;
   - LangGraph `1.2.11`;
8. hosted-runner blocker metadata is present;
9. `phase == complete`;
10. `fatal_error == null`;
11. `failure_count` is integer `0`;
12. `overall == PASS`;
13. exactly 21 gate results exist;
14. gate names are unique;
15. the result set exactly matches the canonical 21 gates;
16. every gate has `status == PASS`;
17. every gate has integer `exit_code == 0`;
18. every gate duration is a non-negative number.

Therefore a forged/inconsistent top-level PASS cannot hide a failed, missing, duplicated or unexpected gate.

## Validated Roadmap 7 candidate

The Roadmap 7 candidate that completed the local functional gate was:

```text
branch = roadmap7/integration-candidate-v1
commit = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
local_release_gate = PASS 21/21
```

PR #68 was subsequently merged into `main` as:

```text
merge_commit = 58feb12531982342bf3c12b9e8b8c61a5e819c5f
```

The validator remains useful for independently checking the machine-readable evidence from that run and for future release candidates. The actual JSON evidence file is external to the repository, so its validation is a separate operation from merging this tooling.

## Usage

Find the most recent evidence file:

```powershell
$Evidence = Get-ChildItem "$env:LOCALAPPDATA\metaO\release-gate-evidence\gate-*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
```

Validate it against the exact candidate that produced it:

```powershell
py -3.12 .\scripts\validate_release_evidence.py `
    $Evidence.FullName `
    --expected-commit aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea `
    --expected-branch roadmap7/integration-candidate-v1
```

Valid output:

```text
RELEASE_EVIDENCE = VALID_PASS
BRANCH = roadmap7/integration-candidate-v1
COMMIT = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
GATES = 21
FAILURES = 0
```

For later release candidates, always pass the exact branch and commit recorded in the evidence being checked.

## Exit codes

```text
0 = evidence is a complete valid PASS for the expected branch/SHA
1 = evidence JSON was readable but failed one or more release invariants
2 = evidence file could not be read or parsed
```

Any nonzero result is fail-closed and must not be used as release evidence.

## Tests

`tests/unit/test_release_evidence_validator.py` covers:

- valid complete PASS;
- wrong SHA;
- missing/duplicated gate;
- a failed gate hidden behind top-level PASS;
- dirty worktree/fatal error;
- Python bool-vs-int edge case for `failure_count`;
- UTF-8 BOM produced by Windows PowerShell environments.

These tests validate the evidence checker itself. They do not substitute for the 21 functional release gates.
