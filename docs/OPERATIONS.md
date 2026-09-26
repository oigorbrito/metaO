# metaO Operations

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Last reconciled commit: `4bedae3715ff30ce36cb183417f136400f1a8c91`
Date reconciled: 2026-09-25

Current-head qualification note: the executable initialization evidence recorded below was produced at `9dbdf542eaad59e5cc80b8a1a845bf527a36893c`. It remains historical evidence and must not be promoted to current-head qualification without rerunning the exact path at `4bedae3715ff30ce36cb183417f136400f1a8c91`.

## Purpose

This document defines the operational rules for the post-MVP baseline.

## Operational truth

- GitHub is the persistent engineering ledger.
- Issues own execution state.
- PRs own reviewable change surfaces.
- Documentation owns durable contracts and architecture, not ephemeral task tracking.
- An implementation is not operationally resolved merely because code or tests exist; the required executable gate must run and satisfy its acceptance conditions.

## Canonical initialization evidence

The canonical Python operator initialization path is qualified on integrated `main@9dbdf542eaad59e5cc80b8a1a845bf527a36893c` by a clean-room Windows execution using Python 3.12.10 and an isolated virtual environment.

Observed qualification:

```text
CLEAN_CLONE = YES
ISOLATED_VENV = YES
INSTALLED_CLI = YES
CLI_HELP_INCLUDES_DOCTOR = YES
UNIT_REGRESSION = 487/487 PASS
CANONICAL_INITIALIZATION_E2E = PASS
FINAL_WORKTREE = CLEAN
INITIALIZATION_RESOLVED = YES
```

The canonical initialization E2E executes the installed `metao` console command and traverses:

```text
clean environment
-> doctor
-> canonical factory loading
-> declarative runtime catalog
-> real LangGraph runtime
-> required runtime certification
-> runtime admission
-> runtime visibility/certificate persistence
-> mission execution
-> ACCEPTED
-> separate-process inspect
-> execution/evidence/proof observable
```

This evidence is local operational evidence for the integrated initialization path. It is not hosted-CI evidence and does not imply provider-backed external-system success.

## Known operational blockers

- hosted GitHub Actions remains externally blocked before configured steps on the historical release path under #71;
- exact release-evidence JSON revalidation depends on the external file being available;
- artifacts under `.smag/` and `experiments/rust-chassis-a/target/` are local workspace residue and not canonical evidence.

The #71 hosted-runner blocker is independent from the initialization result above: `LOCAL_INITIALIZATION_E2E_PASS != HOSTED_CI_PASS`.

## Release rules

- release evidence must bind to exact commit and branch;
- old evidence does not regain authority after newer state exists;
- historical local PASS is not a substitute for current-head validation;
- block classifications must remain distinct from product failures;
- local evidence must not be promoted to hosted-CI or real-provider evidence without those contexts executing.

## Operational readiness

Operational readiness means the current baseline can be repeated locally and reasoned about from durable evidence, with external infrastructure blockers explicitly separated.

The operator initialization requirement is satisfied for the reconciled source state above. This statement does not by itself assert final project closure or full post-MVP operational readiness across every capability domain.
