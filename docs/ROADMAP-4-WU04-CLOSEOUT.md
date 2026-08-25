# Roadmap 4 WU04 — Certified Onboarding Closeout

## Functional scope status

Roadmap 4 functional implementation is complete.

The roadmap composed previously separate work into one declarative onboarding path without adding another orchestrator SDK to metaO Core.

## Work units

### WU01 — Declarative Certified Runtime Onboarding V1

Implemented:

- Roadmap 2 deterministic runtime feedback composed into the Roadmap 3 certification stack;
- explicit `certification.mode=required` manifest path;
- explicit safe probe configuration;
- certification persistence before operational admission;
- legacy manifest compatibility during migration;
- shared SQLite path support for runtime controls, feedback and certification;
- quarantine/live health precedence preserved over feedback/certification.

PR: #45.

### WU02 — Passed Certificate Reuse V1

Implemented:

- opt-in `reuse_passed=true`;
- only persisted PASS certificates may bypass a fresh probe;
- exact orchestrator id binding;
- exact runtime version binding;
- exact probe execution-id binding;
- missing/failed/mismatched certificates never bypass the active probe path;
- restart-oriented SQLite reuse tests prepared.

PR: #46.

### WU03 — Real Declarative Certified Runtimes V1

Prepared real SDK integration evidence for:

- LangGraph 1.2.11;
- CrewAI 1.15.16;
- one declarative manifest containing both runtimes;
- first-load active certification;
- durable SQLite PASS certificates;
- restart admission from persisted PASS without re-running certification probes.

No paid external model/provider is required for the sandbox scenario.

PR: #47.

## Resulting architecture

```text
Mission / operator startup
        |
        v
Declarative Runtime Manifest
        |
        v
Trusted Runtime Plugin Factory
        |
        +--> legacy compatibility path (temporary migration support)
        |
        +--> certification.mode=required
                 |
                 +--> exact persisted PASS reusable? -- yes --> strict certificate binding
                 |                                      |
                 |                                      v
                 +--> no --> active conformance probe -> durable certificate
                                                        |
                                                        v
                                              Runtime Admission Gate
                                                        |
                                                        v
                                                Registry + Catalog
                                                        |
                                      +-----------------+-----------------+
                                      |                                   |
                                      v                                   v
                           Durable Quarantine / Health          Historical Feedback EMA
                                      |                                   |
                                      +-----------------+-----------------+
                                                        |
                                                        v
                                                Deterministic Routing
                                                        |
                                                        v
                                           Existing Policy / Budget /
                                          Approval / Acceptance Authority
```

## Authority invariants

- `ORCHESTRATOR_DONE != METAO_ACCEPTED` remains unchanged.
- Certification authorizes onboarding only; it never accepts a mission.
- Quarantine and live health remain operationally authoritative.
- Feedback remains advisory and deterministic.
- Policy, budget, approval and independent acceptance remain above runtime execution.
- Runtime-specific SDK imports remain inside adapters/plugins.

## Execution evidence status

The repository has prior green evidence through Roadmap 2 WU04, including 171/171 unit tests and real LangGraph/CrewAI sandbox execution from earlier merged work.

For Roadmap 2 WU05 and Roadmaps 3–4, new executable CI evidence is still pending because GitHub-hosted Actions jobs fail before their first step is allocated. This infrastructure condition is intentionally being ignored for forward implementation at the user's direction.

Therefore:

- implementation status may be `COMPLETE`;
- remote test status is `PENDING`;
- merge status is `PENDING`;
- no unexecuted test is labeled PASS.

## Explicit non-claims

Roadmap 4 does not establish:

- production deployment readiness;
- external paid-provider/model behavior;
- certificate freshness or expiry policy;
- certificate revocation;
- source-code or artifact cryptographic attestation;
- protection from a plugin changing behavior without changing its declared runtime version;
- production SLOs/load characteristics;
- support for a third orchestrator framework.

## Recommended next roadmap

Roadmap 5 should address **Certification Lifecycle / Freshness / Revocation** before expanding the number of supported frameworks.

Priority order:

1. explicit certificate validity/freshness semantics;
2. operator-driven certificate revocation/invalidation;
3. deterministic re-certification policy after expiry/revocation/version change;
4. CLI visibility for certificate history/status;
5. real-runtime regression for expiry/re-certification;
6. only then evaluate a third orchestrator runtime.

This prevents durable PASS certificates from becoming indefinite trust tokens.

## Gate

```text
ROADMAP_4_FUNCTIONAL_SCOPE = COMPLETE
DECLARATIVE_CERTIFIED_ONBOARDING = IMPLEMENTED
DETERMINISTIC_FEEDBACK_COMPOSED = YES
PASSED_CERTIFICATE_REUSE = IMPLEMENTED
REAL_LANGGRAPH_CREWAI_SCENARIO = PREPARED
CORE_SDK_NEUTRALITY = PRESERVED
LEARNED_ROUTING = NO
THIRD_FRAMEWORK = NO
REMOTE_EXECUTION_GATE = PENDING
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```
