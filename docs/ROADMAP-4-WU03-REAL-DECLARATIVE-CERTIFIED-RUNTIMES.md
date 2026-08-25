# Roadmap 4 WU03 — Real Declarative Certified Runtimes V1

## Goal

Exercise the composed Roadmap 4 path with the two real orchestrator SDKs already
accepted as repository sandbox targets:

- LangGraph 1.2.11
- CrewAI 1.15.16

No third framework is introduced.

## Evidence scenario

A single declarative manifest contains both runtime plugin factories with:

- `certification.mode=required`;
- `reuse_passed=true`;
- explicit deterministic probe execution ids;
- framework-neutral routing metadata.

First construction:

1. plugin factories construct real SDK runtimes;
2. LangGraph compiled graph executes its certification probe;
3. CrewAI Agent/Task/Crew executes through a deterministic local `BaseLLM`;
4. both adapters normalize evidence through the common metaO boundary;
5. both certificates are persisted to SQLite;
6. only passing runtimes are admitted into the same registry/catalog.

Restart construction:

1. new real SDK runtime objects are constructed by the same plugin factories;
2. exact persisted PASS certificates are found;
3. strict id/version/probe bindings are checked;
4. both runtimes are admitted without executing either certification probe again;
5. certificate histories remain one immutable record per runtime/probe identity.

## What this proves when executable

- declarative onboarding can drive both real SDK adapters;
- certification is framework-neutral;
- durable certificate reuse survives process restart;
- CrewAI does not require a paid model/provider for the sandbox proof;
- no framework SDK enters metaO Core/control-plane.

## What this does not claim

- external paid model/provider execution;
- production reliability or SLOs;
- source-code attestation;
- automatic version correctness if a plugin changes behavior without bumping its runtime version;
- third-framework support.

## Prepared test

`tests/integration/test_r4_wu03_real_declarative_certified_runtimes.py`

Scenarios:

1. pinned SDK versions are exact;
2. first manifest load actively certifies both real runtimes and persists PASS;
3. restart reuses both PASS certificates without invoking either SDK runtime.

## Gate

```text
REAL_DECLARATIVE_CERTIFICATION = PREPARED
LANGGRAPH_VERSION = 1.2.11
CREWAI_VERSION = 1.15.16
FIRST_LOAD_ACTIVE_PROBE = EXPECTED
RESTART_CERTIFICATE_REUSE = EXPECTED
PAID_PROVIDER_REQUIRED = NO
THIRD_FRAMEWORK = NO
REMOTE_TEST_EXECUTION = PENDING
MERGE_GATE = PENDING
```
