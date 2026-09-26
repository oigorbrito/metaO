# GitHub CLI self-hosted pilot runner

This runbook provisions the dedicated GitHub Actions runner used by the metaO #360 operational pilot.

## Trust boundary

The runner is repository-scoped to `oigorbrito/metaO` and must carry the custom label `metao-project-pilot` in addition to GitHub's standard `self-hosted`, `Linux`, and `X64` labels.

The installer never accepts a registration token as an argument and never writes one to a file. It requests a one-time token from GitHub with the already-authenticated `gh` CLI, passes it directly to the official runner `config.sh`, then unsets it.

Installer success only proves that the runner package was verified, configured, registered, and its service was started. It is not project acceptance.

## Prerequisites

Use a dedicated Linux x64 host or VM with:

- Python 3.13+
- `gh`
- `curl`
- `tar`
- `sha256sum`
- `git`
- `ssh`
- `scp`
- `sudo`
- outbound HTTPS to GitHub and, later, the configured model providers

Authenticate GitHub CLI as an account/token authorized to administer repository Actions runners:

```bash
gh auth login
gh auth status
```

The `gh` identity must be able to call:

```text
POST /repos/oigorbrito/metaO/actions/runners/registration-token
GET  /repos/oigorbrito/metaO/actions/runners
```

Do not export a GitHub token into project execution context or logs.

## Install/register

The default pinned GitHub Actions runner release is `v2.337.0`. The installer fetches that exact release through the GitHub API, selects its linux-x64 archive and verifies the release asset's published SHA-256 digest before extraction. A different exact release tag can be selected explicitly with `METAO_ACTIONS_RUNNER_VERSION=vMAJOR.MINOR.PATCH`; there is no implicit `latest` path.

From a checkout containing this script:

```bash
METAO_RUNNER_NAME=metao-project-pilot-01 \
  bash scripts/install_metao_self_hosted_runner.sh
```

Optional installation location and exact runner version:

```bash
METAO_RUNNER_INSTALL_DIR=/opt/metao/actions-runner \
METAO_RUNNER_NAME=metao-project-pilot-01 \
METAO_ACTIONS_RUNNER_VERSION=v2.337.0 \
  bash scripts/install_metao_self_hosted_runner.sh
```

The directory must be absolute, writable by the invoking user, and empty on the first installation. Service installation uses `sudo` through the official `svc.sh` helper.

On a repeated invocation, an existing local configuration is accepted only when `svc.sh` is present and GitHub's runner registry contains the same runner name with all required labels. A local/remote mismatch fails closed rather than silently replacing another runner.

Expected bounded output resembles:

```json
{"installer":"PASS","repository":"oigorbrito/metaO","runner_name":"metao-project-pilot-01","runner_label":"metao-project-pilot","runner_version":"v2.337.0","runner_asset_sha256":"<published sha256>","already_configured":false,"registration_token_emitted":false,"credentials_emitted":false,"pilot_operational_pass":false}
```

`installer=PASS` is not `RUNNER_READINESS=PASS` and is not `#360_OPERATIONAL_PASS`.

## Dispatch the secret-free readiness bridge

The readiness bridge is already landed on `main`. Qualify the exact current operational head:

```bash
bash scripts/dispatch_metao_runner_readiness.sh \
  f101d80dfc8658b780a9b44da72716dd91f34953
```

The helper verifies that the SHA exists in `oigorbrito/metaO`, then submits:

```text
Self-Hosted Runner Readiness Bridge
ref: main
target_head: exact supplied SHA
```

Observe runs with:

```bash
gh run list \
  --repo oigorbrito/metaO \
  --workflow self-hosted-runner-readiness-bridge.yml \
  --event workflow_dispatch \
  --limit 5
```

Then inspect the selected run:

```bash
gh run view RUN_ID --repo oigorbrito/metaO --log
```

Only an actually executed run whose bounded evidence contains `bootstrap_readiness=PASS` establishes runner readiness. Submitted, queued, skipped, cancelled, or no-run states are not PASS.

## After readiness

Only after exact-head runner readiness is established:

1. configure the two distinct SSH execution hosts and corresponding repository secrets;
2. configure `METAO_OPENAI_API_KEY` and `METAO_GEMINI_API_KEY`;
3. dispatch the exact-head fenced multi-provider pilot;
4. require the no-provider-call preflight to pass first;
5. require the complete provider-backed/cross-host/corrective-replan path to finish with `PROJECT_ACCEPTED`;
6. only then consider `#360_OPERATIONAL_PASS=YES`.

Do not put credentials, host values, registration tokens, private keys, or provider keys in `ExecutionRequest.context`, traceability records, artifacts, PR bodies, or logs.
