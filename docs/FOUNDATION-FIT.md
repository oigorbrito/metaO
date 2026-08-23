# Foundation Fit — Conductor

Status: L5_EXECUTION_REQUESTED

## Candidate

```text
DONOR_REPO = conductor-oss/conductor
DONOR_COMMIT = b54f0d4ee546c1053367e1c14405c5396c17bfb1
EXECUTABLE_SERVER_PIN = 3.32.0
ROLE = PRIMARY FOUNDATION CANDIDATE
```

The source donor pin records the audited Conductor source state. The executable pin is the published GA server version used by the Conductor CLI's own blocking E2E path and is intentionally reproducible rather than `latest`.

The independently executed fit suite must prove a real Conductor server, real workflow, worker polling/update, durable state, retry, timeout, pause/resume, process restart recovery, and a thin HTTP boundary that does not require a Conductor SDK import in metaO Core.

No foundation decision is final until the real-path fit run passes.
