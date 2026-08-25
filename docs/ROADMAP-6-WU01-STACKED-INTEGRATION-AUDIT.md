# Roadmap 6 WU01 — Stacked Integration Audit

## Objective

Make the current unmerged topology explicit before adding a third orchestrator
framework.

The hosted GitHub Actions runner issue was intentionally not allowed to stop
functional development. That produced a long, auditable stack of draft PRs, but
`main` remains at the last executed/merged Roadmap 2 WU04 baseline.

This work unit does not merge or rewrite history. It identifies the canonical
integration path and missing evidence artifacts.

## Merged baseline

`main = 628b73409aa596bdcea7cf39136f455a0c220b05`

Last genuinely executed merged full regression: `171/171 PASS`.

## Parallel Roadmap 2 branches

Two PRs were created directly from `main` and are not ancestors of the later
Roadmap 3-5 stack:

| PR | Scope | Relationship to later stack |
|---|---|---|
| #38 | Roadmap 2 WU05 deterministic runtime feedback | production modules were explicitly recomposed in #45; original focused test/doc/workflow are missing from the current top head |
| #39 | Roadmap 2 WU06 closeout/readiness | documentation-only; not present in the current top head |

## Linear functional stack

The following chain is linear and each head is the base of the next PR:

```text
main
  -> #40 R3 WU01 Runtime Conformance Harness
  -> #41 R3 WU02 Runtime Admission Gate
  -> #42 R3 WU03 Durable Runtime Certification
  -> #43 R3 WU04 Real Runtime Certification Regression
  -> #44 R3 WU05 Closeout
  -> #45 R4 WU01 Declarative Certified Runtime Onboarding
  -> #46 R4 WU02 Passed Certificate Reuse
  -> #47 R4 WU03 Real Declarative Certified Runtimes
  -> #48 R4 WU04 Closeout
  -> #49 R5 WU01 Certificate Freshness
  -> #50 R5 WU02 Durable Certificate Revocation
  -> #51 R5 WU03 Certification Lifecycle CLI
  -> #52 R5 WU04 Real Certificate Lifecycle Regression
  -> #53 R5 WU05 Latest Certification Verdict Authority
  -> #54 R5 WU06 Closeout
```

Current top functional head before Roadmap 6:

`roadmap5/wu06-closeout-readiness @ 5ff6e9b3969fa3671a5ac92285f5407fced75387`

## Roadmap 2 WU05 reconciliation

PR #38 changed seven files:

- `.github/workflows/roadmap2-runtime-feedback.yml`
- `docs/ROADMAP-2-WU05-DETERMINISTIC-RUNTIME-FEEDBACK.md`
- `src/metao/feedback_catalog.py`
- `src/metao/runtime_factory.py`
- `src/metao/runtime_feedback.py`
- `src/metao/sqlite_runtime_feedback.py`
- `tests/unit/test_roadmap_2_work_unit_05.py`

The current top head contains the WU05 production capability through the explicit
Roadmap 4 composition.

Exact blob reuse confirmed for:

- `src/metao/runtime_feedback.py` = `639addd594dda910a5b69909f3c56a7be36ab190`
- `src/metao/feedback_catalog.py` = `cafd32db7fdd7be283c5d929e1718bd478f259d6`
- `src/metao/sqlite_runtime_feedback.py` = `6014d1e38b6be94bd409d4b944653b48ad9effa4`

`runtime_factory.py` is intentionally no longer byte-identical to #38 because
Roadmaps 4 and 5 compose certification, freshness, revocation and lifecycle
semantics around the feedback overlay.

Missing from the current top head and therefore required for canonical
consolidation:

- `tests/unit/test_roadmap_2_work_unit_05.py`
- `docs/ROADMAP-2-WU05-DETERMINISTIC-RUNTIME-FEEDBACK.md`
- `.github/workflows/roadmap2-runtime-feedback.yml`

The canonical candidate must import those evidence artifacts without replacing
or reverting the newer `runtime_factory.py`.

## Roadmap 2 closeout reconciliation

PR #39 is documentation-only and changes:

- `docs/ROADMAP-2-CLOSEOUT.md`
- `docs/RELEASE-READINESS.md`

`docs/ROADMAP-2-CLOSEOUT.md` is absent from the current top head.

The old #39 `RELEASE-READINESS.md` text is no longer sufficient because the
intended candidate now includes Roadmaps 3-5. The consolidation should therefore
update release readiness to the current cumulative state rather than blindly
copy the old file.

## Canonical integration strategy

Do **not** merge the entire chain one PR at a time while executable CI remains
unavailable and do not cherry-pick #38 production code over the newer stack.

Instead create one explicit integration candidate from the current top head:

```text
roadmap6/integration-candidate-v1
```

That candidate should:

1. inherit the complete linear #40-#54 history;
2. add only the missing #38 evidence artifacts;
3. add the missing Roadmap 2 closeout history where still useful;
4. refresh `docs/RELEASE-READINESS.md` for the cumulative candidate;
5. add a single consolidated regression workflow covering unit, real-runtime,
   Block O and SDK-neutral boundaries;
6. expose one PR directly against `main` as the canonical review/integration
   surface;
7. leave the old stacked PRs open/draft until the candidate is executable and
   reconciled, so audit history is not lost.

## Duplicate/divergence policy

For each file present in both an older parallel PR and the top stack:

- identical production blob: keep the top-stack file once;
- intentionally evolved production file: keep the newest top-stack semantics;
- missing focused test/doc/workflow: import it;
- conflicting behavior: stop and resolve explicitly before calling the candidate
  coherent.

No silent cherry-pick overwrite is allowed.

## Integration gate

A canonical candidate is only merge-eligible after executable evidence exists
for all of the following:

1. full unit suite;
2. Roadmap 2 WU05 focused deterministic feedback suite;
3. Roadmap 3 conformance/admission/certification suites;
4. Roadmap 4 certified onboarding/reuse suites;
5. Roadmap 5 lifecycle/freshness/revocation/latest-verdict suites;
6. real LangGraph 1.2.11 regression;
7. real CrewAI 1.15.16 regression;
8. Block O O1-O5 regression;
9. SDK-neutral Core/control-plane boundary;
10. installed CLI smoke/compatibility.

## Status

```text
STACK_TOPOLOGY_AUDITED = YES
LINEAR_FUNCTIONAL_CHAIN = #40-#54
PARALLEL_PR_38 = PARTIALLY_RECOMPOSED
PARALLEL_PR_39 = DOCUMENTATION_ONLY_OUTSIDE_CHAIN
CANONICAL_INTEGRATION_HEAD = NOT_YET_CREATED
THIRD_RUNTIME_ADMISSION = DEFERRED_UNTIL_CONSOLIDATION
REMOTE_EXECUTION = PENDING
```

No merge or test PASS is claimed by this audit.
