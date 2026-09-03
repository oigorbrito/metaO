# CI Observation Limitation

## Finding
The available GitHub integration exposes commit-associated workflow lookup through a wrapper that filters results to pull-request-triggered workflow runs.

Therefore:
- an empty result for a branch push does not establish that no push workflow executed;
- it establishes only that no qualifying pull-request-triggered run was returned by that observation path.

## Consequence
Workflow execution claims must distinguish:
1. repository execution absent;
2. execution exists but is not observable through the current connector;
3. execution is observable with jobs/steps/logs.

Until direct run listing or an equivalent receipt is available, push-triggered workflow validation is NOT_OBSERVABLE, not NOT_EXECUTED.

## Required evidence for PASS_EXECUTED
A visible workflow run plus at least one repository command/job receipt with successful completion.
