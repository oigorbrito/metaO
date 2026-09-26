# Project Multi-Provider Pilot Runbook

This runbook moves #360 from PREPARED/NOT_RUN to an evidence-backed operational verdict.

## Preferred execution path while #71 remains active

Use the dedicated workflow `Project Multi-Provider Supervision Pilot Self-Hosted` on a runner carrying all labels:

- `self-hosted`
- `linux`
- `x64`
- `metao-project-pilot`

Do not retarget an arbitrary shared runner to satisfy this workflow. The dedicated label is part of the execution boundary.

## Runner prerequisites

The runner must provide:

- Python 3.13+
- Git
- OpenSSH client (`ssh`, `scp`)
- outbound HTTPS access required by OpenAI/Gemini APIs and Python package installation
- network reachability to both configured SSH hosts

The workflow installs `openai-agents==0.20.0` itself.

## Required repository secrets

Provider credentials:

- `METAO_OPENAI_API_KEY`
- `METAO_GEMINI_API_KEY`

SSH endpoint configuration:

- `METAO_SSH_SMOKE_SOURCE_HOST`
- `METAO_SSH_SMOKE_DESTINATION_HOST`
- `METAO_SSH_SMOKE_SOURCE_USER`
- `METAO_SSH_SMOKE_DESTINATION_USER`
- `METAO_SSH_SMOKE_SOURCE_PORT` (optional; defaults to 22 in the harness)
- `METAO_SSH_SMOKE_DESTINATION_PORT` (optional; defaults to 22 in the harness)
- `METAO_SSH_SMOKE_KNOWN_HOSTS`
- `METAO_SSH_SMOKE_IDENTITY` when runner-side agent authentication is not preconfigured

The source and destination hosts must be distinct.

## Remote host prerequisites

Each host must provide:

- Git
- Python 3
- permission for the configured SSH user to create and delete disposable `/tmp/metao-project-pilot.*` directories

No persistent repository is required. The pilot creates disposable repositories and attempts cleanup on both hosts.

## Dispatch

Dispatch the exact pilot head using the workflow input:

`I_AUTHORIZE_METAO_MULTI_PROVIDER_PROJECT_PILOT`

The workflow first executes `scripts/project_multi_provider_preflight.py`. The preflight:

- makes no provider API calls;
- checks required configuration without printing secret values;
- checks local Git/Python/SSH/SCP availability;
- verifies strict SSH connectivity to both hosts;
- checks remote Git/Python availability;
- verifies temporary-directory create/delete permission;
- emits bounded JSON evidence with `provider_calls_made=false`.

Only after the preflight succeeds may the provider-backed pilot job run.

## Operational PASS criteria

A run is an operational PASS only when the exact-head provider-backed job completes and its bounded evidence asserts all of the following:

- `project_verdict == PROJECT_ACCEPTED`
- both `executor-gemini` and `executor-openai` were used
- both `provider-google` and `provider-openai` were used
- typed capacity failure injection occurred
- provider-diverse failover occurred
- independent verification failure occurred
- corrective work was created and executed
- cross-host checkpoint transfer occurred
- checkpoint SHA lineage contains the required transitions
- credentials and remote paths were not emitted
- `operational_pilot == PASS`

A successful preflight alone is not an operational PASS. A successful single provider call is not an operational PASS. A skipped or pre-step-failed workflow is not an operational PASS.

## After PASS

Preserve the exact workflow/run identifiers and exact Git head in #546, then requalify the stacked PR chain for merge readiness. `mergeable=true` alone is insufficient.
