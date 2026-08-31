# metaO Architecture

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

## Purpose

This document states the frozen architecture for the current post-MVP baseline.

## Frozen architecture

```text
Mission
-> Strategy / Selection
-> Policy / Budget
-> OrchestratorContract
-> Runtime Adapter
-> Orchestrator
-> Evidence
-> Independent Acceptance
-> Accept / Replan / Failover / Block
```

## Invariants

- Replacing an orchestrator, including agents, tools, memory, prompts, routing, and workflows, must not require changing metaO Core.
- Orchestrator terminal success is not the same as metaO acceptance.
- Policy, budget, approval, quarantine, retry, and acceptance remain metaO-owned.
- Framework SDKs stay behind adapters.
- Core must not import framework-specific orchestrator SDKs.

## Canonical implementation boundary

Current repository surface:

- `src/metao/core.py` defines the contract types, acceptance envelope, registry, and result shapes.
- `src/metao/acceptance.py` defines independent acceptance semantics and deterministic replay.
- `src/metao/runtime.py` and `src/metao/runtime_*` define operational invariants for leases, fencing, recovery, admission, certification, and security-adjacent controls.
- `src/metao/adapters/` contains framework adapters.
- `src/metao/operator.py`, `src/metao/control_plane.py`, and related modules wire the public control-plane behavior.

## Architecture status

- Frozen structure: yes.
- Product direction: Rust-native.
- Current executable repository: Python.
- Architecture change required for additional framework support: no, if the adapter boundary is respected.

## Explicit non-goals

- no fourth runtime for feature count;
- no learned routing as a requirement for baseline authority;
- no cloud/Kubernetes/distributed DB requirement for current baseline;
- no hand-rolled cryptography;
- no acceptance authority in orchestrator runtimes.

