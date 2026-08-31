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
