# GitHub Adapter Cost Benchmark Protocol

## Question
For the same workflow, which routing minimizes total operational cost while preserving correctness and governance?

## Arms
- AGENT_DIRECT: agent performs GitHub operations through its own tool path.
- METAO_DIRECT: metaO performs deterministic GitHub operations without LLM reasoning.
- HYBRID: agent performs reasoning; metaO performs deterministic GitHub operations.

## Workload classes
1. Issue read + normalization.
2. PR state + CI status aggregation.
3. Deterministic PR lifecycle operation.
4. CI failure triage requiring reasoning.

## Required measurements
For each run record:
- workflow identifier;
- arm;
- commit/version;
- model/provider;
- input tokens;
- output tokens;
- LLM calls;
- GitHub API calls;
- retries;
- wall-clock latency;
- success/failure;
- governance denials;
- recovery actions.

## Primary endpoint
Median total cost per successfully completed workflow.

## Secondary endpoints
- p95 latency;
- API-call count;
- LLM token count;
- failure/retry rate;
- governance violation rate.

## Decision rule
No architecture preference is inferred from a single run. Compare repeated paired runs on identical workloads. Report uncertainty and raw measurements.

## Preconditions
- adapter baseline must have at least one PASS_EXECUTED receipt;
- GitHub operation semantics must be equivalent across arms;
- credentials, repository and workload must be held constant where possible.
