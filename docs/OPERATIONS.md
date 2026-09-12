# metaO Operations

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

## Purpose

This document defines the operational rules for the post-MVP baseline.

## Operational truth

- GitHub is the persistent engineering ledger.
- Issues own execution state.
- PRs own reviewable change surfaces.
- Documentation owns durable contracts and architecture, not ephemeral task tracking.

## Known operational blockers

- hosted GitHub Actions remains externally blocked before configured steps on the historical release path;
- exact release-evidence JSON revalidation depends on the external file being available;
- artifacts under `.smag/` and `experiments/rust-chassis-a/target/` are local workspace residue and not canonical evidence.

## Release rules

- release evidence must bind to exact commit and branch;
- old evidence does not regain authority after newer state exists;
- historical local PASS is not a substitute for current-head validation;
- block classifications must remain distinct from product failures.

## Operational readiness

Operational readiness means the current baseline can be repeated locally and reasoned about from durable evidence, with external infrastructure blockers explicitly separated.

## Canonical operator quickstart

The canonical executable operator surface is the Python package declared in `pyproject.toml`:

```text
package = metao-control-plane
console = metao
entrypoint = metao.entrypoint:main
python = >=3.12
default_db = .metao/metao.db
factory = METAO_OPERATOR_FACTORY or --factory module:function
quickstart_factory = metao.examples.readme_factory:create_operator
quickstart_mission = examples/readme_mission.json
```

The operator quickstart in `README.md` is executable evidence, not editorial guidance. Its local verification harness is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-readme-quickstart-gate.ps1
```

The harness installs the package in an isolated Python 3.12 virtual environment, invokes the installed `metao` command, runs `doctor`, lists runtimes, executes a first mission to `ACCEPTED`, and verifies `status` plus `inspect` against the persisted SQLite record from a new process.

Evidence is written outside the repository under:

```text
%LOCALAPPDATA%\metaO\readme-quickstart-evidence\
```

Release-quality quickstart evidence requires:

```text
clean_worktree = true
failure_count = 0
overall = PASS
```

A dirty-worktree run with `-AllowDirty` is diagnostic only.
