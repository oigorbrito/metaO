# Roadmap 5 WU04 — Real Certificate Lifecycle Regression V1

## Objective

Exercise Roadmap 5 freshness + revocation + recertification semantics against the
two real orchestrator SDK integrations already accepted as repository sandboxes.

## Runtime targets

- LangGraph `1.2.11`
- CrewAI `1.15.16`

CrewAI uses the deterministic local `BaseLLM` sandbox. No external paid provider
or model key is required.

## Real lifecycle scenarios prepared

### First certification + in-window reuse

At `now=100`:

- real LangGraph compiled graph executes the certification probe;
- real CrewAI Agent/Task/Crew/Process executes the certification probe;
- each produces one timestamped PASS generation in SQLite.

At `now=120`, with `max_age_seconds=60`:

- both certificates are fresh;
- both are reused;
- neither SDK runtime executes a new certification probe.

### Expiry

At `now=161` after certificates issued at `100`:

- both PASS generations are stale;
- both real SDK probes execute again;
- each runtime receives a second immutable certificate generation.

### Selective revocation

After the first certification:

- revoke only the LangGraph certificate;
- keep CrewAI certificate unrevoked and fresh;
- next load actively recertifies LangGraph only;
- CrewAI reuses its existing PASS without executing the Crew runtime;
- old LangGraph generation remains revocation-audited;
- new LangGraph generation remains unrevoked.

### Reuse after revocation-driven recertification

After LangGraph has generated the replacement PASS:

- next in-window load reuses the new generation;
- neither LangGraph nor CrewAI executes the certification probe again.

## Preserved invariants

- Core/control plane contains no framework SDK imports;
- revocation is per certificate generation;
- quarantine remains separate;
- freshness uses explicit deterministic time inputs in tests;
- no learned trust/routing logic;
- no third orchestrator framework;
- no production SLO claim.

## Evidence gate

The workflow installs exact pinned versions and runs:

1. WU04 real lifecycle integration;
2. Roadmap 4 real declarative certification regression;
3. Roadmap 2 real runtime sandbox regression;
4. WU01-WU03 unit regressions;
5. full unit suite;
6. SDK-neutral boundary check.

## Status

`REAL_CERTIFICATE_LIFECYCLE_SCENARIO = PREPARED`

`REAL_EXPIRY_RECERTIFICATION = PREPARED`

`REAL_SELECTIVE_REVOCATION = PREPARED`

`REAL_REUSE_AFTER_RECERTIFICATION = PREPARED`

`REMOTE_EXECUTION = PENDING`

No PASS is claimed until executable output exists.
