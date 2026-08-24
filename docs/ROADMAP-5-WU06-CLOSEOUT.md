# Roadmap 5 WU06 — Certification Lifecycle Closeout

## Roadmap objective

Roadmap 5 prevents a durable runtime conformance PASS from becoming permanent or
silently regaining authority after newer negative evidence.

It adds lifecycle controls around the certified onboarding path created in
Roadmaps 3 and 4 without changing the metaO authority model.

## Work units

### WU01 — Certificate Freshness & Deterministic Recertification

PR #49.

Implemented:

- optional `certification.max_age_seconds`;
- immutable timestamped certificate generations;
- deterministic freshness calculation;
- stale/legacy PASS forces active recertification;
- SQLite migration preserving historical rows.

### WU02 — Durable Certificate Revocation

PR #50.

Implemented:

- immutable revocation per exact certificate generation;
- in-memory and SQLite revocation stores;
- unknown certificate revocation fails closed;
- revoked PASS cannot be reused;
- new trust requires a new conformance generation;
- revocation remains separate from runtime quarantine.

### WU03 — Certification Lifecycle CLI

PR #51.

Implemented operator commands:

- `runtime-certificates`;
- `runtime-certificate-revoke`;
- `runtime-certificate-revocations`.

The existing mission CLI remains delegated unchanged.

### WU04 — Real Certificate Lifecycle Regression

PR #52.

Prepared real SDK evidence against:

- LangGraph 1.2.11;
- CrewAI 1.15.16 with deterministic local BaseLLM.

Prepared scenarios cover first certification, in-window reuse, expiry-driven
recertification, selective revocation and reuse of the replacement generation.

### WU05 — Latest Certification Verdict Authority

PR #53.

Implemented the lifecycle hardening rule:

> For one exact orchestrator/runtime-version/probe binding, the newest certificate
> generation is the authoritative conformance verdict.

Consequences:

- newer FAIL supersedes every older PASS;
- revoked newest PASS does not resurrect an older PASS;
- stale newest PASS does not fall back to older history;
- a later successful recertification becomes the new reusable verdict;
- once a binding is generational, it remains generational even if TTL/revocation
  configuration is later removed.

## Final lifecycle decision order

For a configured certified runtime:

1. load the trusted plugin;
2. determine the latest exact certificate generation;
3. reuse only if that generation is PASS;
4. reject reuse if that generation is revoked;
5. reject reuse if it is stale under configured freshness policy;
6. otherwise verify exact durable identity/binding and admit;
7. when reuse is unavailable, run the explicit deterministic conformance probe;
8. persist the new PASS/FAIL generation before operational admission;
9. admit only on PASS;
10. after admission, runtime quarantine/live health remain authoritative for
    operational selection.

## Authority boundaries preserved

Certificate lifecycle controls only whether historical conformance evidence can
skip a new onboarding probe.

It does not replace or weaken:

- runtime quarantine;
- live health;
- policy;
- budget;
- human approval;
- independent acceptance;
- failover/replanning;
- deterministic runtime feedback.

`ORCHESTRATOR_DONE != METAO_ACCEPTED` remains unchanged.

## Security / architecture invariants

- SDK code remains in adapters/plugins;
- certificate lifecycle code is framework-neutral;
- no learned routing or learned trust thresholds;
- no automatic unrevoke;
- no remote PKI/signature claim;
- no cloud/Kubernetes requirement;
- no third orchestrator framework introduced in this roadmap.

## Test evidence status

Repository artifacts now contain focused unit suites and real-runtime integration
workflows for WU01-WU05.

However, the current hosted GitHub Actions environment is failing before job
steps execute. The operator explicitly chose to continue feature development
without treating that external runner allocation issue as a workflow blocker.

Therefore the only valid status is:

```text
ROADMAP_5_FUNCTIONAL_IMPLEMENTATION = COMPLETE
ROADMAP_5_REMOTE_EXECUTION = PENDING
ROADMAP_5_MERGE_GATE = PENDING
ROADMAP_5_PRODUCTION_CLAIM = NO
```

No new Roadmap 5 test is recorded as PASS without executable output.

## Integration debt / next gate

Roadmaps 2 WU05, 3, 4 and 5 currently exist as a long stack of draft PRs rather
than merged `main` history.

Before adding a third orchestrator framework, the next roadmap must first make
that integration state explicit and create a deterministic consolidation gate.

Recommended next scope:

**Roadmap 6 — Stack Consolidation & Third Runtime Readiness**

Suggested order:

1. audit the exact open PR dependency graph;
2. define one canonical integration head containing all intended Roadmap 2-5
   changes exactly once;
3. detect duplicate/divergent implementations introduced by stacked work;
4. prepare a single full regression gate for the consolidated head;
5. only then evaluate and add a third current orchestrator runtime.

This avoids proving a third adapter on top of an integration topology that has
never been executable as one coherent release candidate.
