# Roadmap 6 WU02 — Canonical Integration Candidate V1

## Objective

Create one reviewable integration head containing the intended cumulative metaO
state after Roadmap 2 WU05 and Roadmaps 3-5, without duplicate production code or
loss of focused evidence artifacts.

## Canonical branch

`roadmap6/integration-candidate-v1`

Unlike the intermediate stacked PRs, the canonical PR is opened directly against
`main` so the complete release-candidate delta can be reviewed in one place.

## Construction

Base content:

- complete linear stack #40-#54;
- Roadmap 6 WU01 topology audit.

Reconciled from parallel PR #38 by existing Git blob identity:

- `tests/unit/test_roadmap_2_work_unit_05.py`
- `docs/ROADMAP-2-WU05-DETERMINISTIC-RUNTIME-FEEDBACK.md`
- `.github/workflows/roadmap2-runtime-feedback.yml`

Already present and therefore **not duplicated**:

- `src/metao/runtime_feedback.py`
- `src/metao/feedback_catalog.py`
- `src/metao/sqlite_runtime_feedback.py`

Not imported from #38:

- its historical `runtime_factory.py`, because the later stack intentionally
  evolved that file to compose certification/freshness/revocation semantics.

Reconciled from parallel PR #39:

- `docs/ROADMAP-2-CLOSEOUT.md`

The old #39 `docs/RELEASE-READINESS.md` is superseded by a new cumulative
candidate-readiness document.

## Consolidated regression surface

`.github/workflows/roadmap6-canonical-integration.yml` is the single candidate
gate. It is intentionally redundant with focused historical workflows because
its purpose is to prove the cumulative head, not individual WU ancestry.

The gate covers:

- installed package/CLI smoke;
- focused deterministic runtime feedback;
- complete unit discovery;
- Roadmap 2 real LangGraph/CrewAI sandbox;
- Roadmap 3 real certification;
- Roadmap 4 real declarative certified onboarding;
- Roadmap 5 real certificate lifecycle;
- Block O O1-O5;
- framework SDK import boundary.

## Merge policy

The canonical candidate remains draft and unmerged while executable CI is
unavailable.

When execution becomes available:

1. run the consolidated gate;
2. correct concrete failures on this branch only;
3. repeat until green;
4. compare candidate with `main` one final time;
5. merge the canonical PR only after green evidence;
6. then close/supersede historical stacked PRs with links to the merged canonical
   candidate rather than merging them individually.

This preserves audit history without replaying the same logical changes multiple
times.

## Third runtime rule

No third framework is added inside this WU. A third runtime experiment must branch
from the canonical candidate and use current upstream evidence.

## Status

```text
CANONICAL_INTEGRATION_BRANCH = CREATED
PARALLEL_WU05_EVIDENCE = RECONCILED
ROADMAP_2_CLOSEOUT_HISTORY = RECONCILED
NEWEST_PRODUCTION_SEMANTICS = PRESERVED
CONSOLIDATED_REGRESSION_GATE = PREPARED
CANONICAL_CANDIDATE_EXECUTION = PENDING
CANONICAL_CANDIDATE_MERGE = NO
```
