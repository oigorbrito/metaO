# GitHub Actions hosted-runner support packet

## Purpose

This document is the durable escalation packet for metaO Issue #71.

The repository has a reproducible GitHub-hosted Actions failure that occurs **before repository execution begins**. The common fingerprint is a completed failed job with `steps = null`; in several runs the job logs endpoint also returned `BlobNotFound` or no usable logs.

This must not be classified as a metaO functional test failure because checkout/setup/test steps never start.

## Repository

```text
repository = oigorbrito/metaO
visibility = private
default branch = main
owner/admin = oigorbrito
```

## Reproduction matrix

### Minimal Ubuntu diagnostic — PR #65

```text
run = 32736704068
job = 97461133603
runner = ubuntu-latest
steps = null
logs = BlobNotFound / unavailable
repository checkout = NOT REACHED
```

The workflow contained one minimal hosted job and did not depend on metaO runtime dependencies.

### Cross-OS diagnostic — PR #67

```text
run = 32737346242
macOS job  = 97463231179 -> steps = null
Windows job = 97463231312 -> steps = null; BlobNotFound observed
Ubuntu job  = 97463231320 -> steps = null
```

All three standard hosted OS pools reproduced the same pre-step failure.

### Canonical integration candidate — PR #68

Frozen candidate:

```text
commit = 8d5cd2b3d2d06643c8fcb5f404b2399b78948c68
```

Representative runs:

```text
Roadmap 6 Canonical Integration Candidate
run = 32744523423
job = 97486740996
steps = null

base CI
run = 32744522467
job = 97486737321
steps = null
```

The frozen SHA triggered 25 PR workflows in the same window; all completed as failure before configured steps executed.

Earlier canonical reproduction:

```text
run/job evidence includes job 97474055832
steps = null
```

### Release Evidence Validator — PR #69

```text
run = 32765858781
job = 97555055393
steps = null
```

This workflow is deliberately small and independent of the three-runtime functional gate.

### Repository governance — PR #75

```text
run = 32768247151
job = 97562510856
steps = null
```

PR #75 changed only GitHub templates/documentation and still reproduced the same pre-step failure.

### Label taxonomy — PR #77

```text
run = 32783856579
job = 97611509843
steps = null
```

PR #77 changed one documentation file only and again reproduced the same pre-step failure.

## Common fingerprint

Across the independent reproductions above:

```text
workflow parsing/dispatch is sufficient to create a run/job
job reaches completed/failure
configured job steps are absent: steps = null
checkout is not reached
Python/runtime package installation is not reached
metaO tests are not reached
switching ubuntu/windows/macos does not bypass the failure
small documentation-only PRs reproduce the same behavior
```

Therefore:

```text
CLASSIFICATION = BLOCKED_EXTERNAL_PRE_STEP
METAO_FUNCTIONAL_FAILURE = NO
REMOTE_FUNCTIONAL_TESTS_EXECUTED = NO
```

## What has already been ruled out

- metaO Python/runtime dependency resolution as the cause of the hosted failure;
- one specific workflow definition as the cause;
- one specific standard hosted operating system as the cause;
- application test assertions as the cause;
- the cumulative Roadmap 2-7 diff as the sole trigger;
- the release evidence validator as the sole trigger.

Do not repeatedly rerun these workflows without a new diagnostic hypothesis.

## Manual account/repository checks still required

The current ChatGPT GitHub connector does not expose Billing, hosted-runner entitlement, Actions budget, or repository Actions General settings. These checks therefore require GitHub UI or GitHub Support access.

### Account / billing

Inspect GitHub billing/usage for:

```text
Actions included hosted-runner minutes
remaining usage / billing cycle
Actions budgets or spending limits
Stop usage when budget limit is reached
payment/spending restriction
plan/entitlement state for private-repository hosted Actions
```

Record the observed values in Issue #71. Do not infer them from the failed runs.

### Repository Actions settings

Inspect repository `oigorbrito/metaO` -> Settings -> Actions -> General for:

```text
Actions enabled
allowed actions/reusable workflows policy
workflow permissions
fork/private repository restrictions if any
runner policy / hosted runner availability
```

### Runner/account service state

If billing and repository settings are healthy, escalate to GitHub Support because the evidence is compatible with runner allocation / account routing / log-store failure before job setup.

## Resolution condition

Issue #71 should not be considered resolved merely because one workflow is rerun.

Minimum resolution evidence:

```text
1. a minimal hosted workflow reaches Set up job and at least one configured step;
2. a canonical metaO workflow reaches checkout/setup/test steps;
3. the exact disposition is recorded in #71 and parent #70.
```

Functional PASS remains a separate question from runner recovery.

## Paste-ready GitHub Support case

```text
Subject: Private repository GitHub-hosted Actions jobs fail before Set up job with steps=null across Ubuntu/Windows/macOS

Repository: oigorbrito/metaO (private)

We have a reproducible hosted-runner failure before repository execution. Jobs are created and end in failure, but the jobs API reports steps=null; checkout never starts. In some runs job log retrieval returns BlobNotFound/unavailable logs.

The same fingerprint reproduces on minimal workflows and on all three standard hosted OS families, so it is not specific to our application tests or runtime dependencies.

Representative evidence:
- minimal Ubuntu: run 32736704068, job 97461133603
- cross-OS run 32737346242:
  - macOS 97463231179
  - Windows 97463231312
  - Ubuntu 97463231320
- canonical candidate: run 32744523423, job 97486740996
- basic CI: run 32744522467, job 97486737321
- independent validator: run 32765858781, job 97555055393
- docs-only governance PR: run 32768247151, job 97562510856
- docs-only label taxonomy PR: run 32783856579, job 97611509843

Common result: completed/failure with steps=null before checkout/setup.

Please investigate hosted-runner allocation/account routing/entitlement and the associated log-store failure for this repository/account. We can provide additional run IDs if needed.
```

## Related metaO tracking

```text
#70 canonical Roadmaps 2-7 integration validation
#71 hosted-runner pre-step blocker
#78 this support packet
PR #68 canonical integration candidate
PR #69 release evidence validator
```

## Evidence policy

This packet documents infrastructure evidence only.

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
BLOCKED_EXTERNAL != TEST_FAIL
```
