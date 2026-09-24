# Self-hosted SSH secret-file lifecycle

Credential-backed pilot workflows may materialize two controlled files under `RUNNER_TEMP` after exact-head and authorization fences:

- `metao-pilot-known-hosts`
- `metao-pilot-identity` (optional)

Lifecycle contract:

1. Files are created only after the workflow has passed its trust-boundary checks.
2. Workflows never print file contents or include them in bounded evidence.
3. Cleanup runs with `always()` so it is attempted after success, failure, or cancellation paths that still permit runner steps to execute.
4. Cleanup derives paths from `RUNNER_TEMP` plus hard-coded basenames and refuses deletion if the resolved parent escapes that directory.
5. Missing files are treated as already clean; deletion errors are not silently ignored.
6. Linux and Windows use the same two controlled basenames and equivalent containment semantics.
7. Runner-level emergency termination can prevent any workflow step from running; operators must treat such a runner as requiring host-level sanitation before reuse.

This lifecycle contract does not establish provider execution or project acceptance. `IMPLEMENTATION != EXECUTION` and `NOT_RUN != PASS` remain authoritative.