# GitHub CLI self-hosted pilot runner on Windows

This runbook provisions and qualifies a Windows x64 GitHub Actions runner for metaO using the same repository-scoped trust boundary as the Linux path.

## Trust boundary

The runner is repository-scoped to `oigorbrito/metaO` and carries custom label `metao-project-pilot` plus GitHub's standard `self-hosted`, `Windows`, and `X64` labels.

The installer does not accept a registration token as input and does not persist one. It obtains a one-time token through the already-authenticated GitHub CLI, passes it directly to the official `config.cmd`, then clears the variable.

Installer PASS is not readiness PASS and is not `#360_OPERATIONAL_PASS`.

## Prerequisites

Run 64-bit PowerShell **as Administrator** on Windows x64 with:

- GitHub CLI `gh`
- Git
- OpenSSH client (`ssh`, `scp`)
- outbound HTTPS to GitHub

Authenticate `gh` with an identity allowed to administer repository Actions runners:

```powershell
gh auth login
gh auth status
```

The identity must be able to call:

```text
POST /repos/oigorbrito/metaO/actions/runners/registration-token
GET  /repos/oigorbrito/metaO/actions/runners
```

## Install/register

From a checkout of `main`:

```powershell
git checkout main
git pull --ff-only
$env:METAO_RUNNER_NAME = 'metao-project-pilot-win-01'
powershell -ExecutionPolicy Bypass -File .\scripts\install_metao_self_hosted_runner_windows.ps1
```

Default install directory:

```text
%ProgramData%\metaO\actions-runner-metao-project-pilot
```

Optional absolute directory:

```powershell
$env:METAO_RUNNER_INSTALL_DIR = 'D:\metaO\actions-runner'
```

Default Actions Runner version is pinned to `v2.337.0`. An override must still be an exact `vX.Y.Z` value:

```powershell
$env:METAO_ACTIONS_RUNNER_VERSION = 'v2.337.0'
```

The installer fetches the exact `actions-runner-win-x64-<version>.zip` release asset from the official `actions/runner` repository and verifies the SHA-256 digest published by the GitHub API before extraction.

It configures `config.cmd --unattended --runasservice`, so the process must run elevated. Repeated invocation only accepts an existing local `.runner` when the same runner name exists in the GitHub registry with all required labels; mismatch fails closed.

## Dispatch Windows readiness

After installer PASS:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dispatch_metao_runner_readiness_windows.ps1 `
  f101d80dfc8658b780a9b44da72716dd91f34953
```

This submits the landed workflow `self-hosted-runner-readiness-windows.yml` on `main`. It does not itself establish PASS.

Observe with:

```powershell
gh run list --repo oigorbrito/metaO --workflow self-hosted-runner-readiness-windows.yml --event workflow_dispatch --limit 5
```

Only an actually executed run with bounded output containing `bootstrap_readiness=PASS` establishes Windows runner readiness.

## Current pilot limitation

The existing credential-backed multi-provider project pilot workflow is Linux-targeted and uses the Linux-specific execution path. Windows readiness therefore proves that a Windows runner can be provisioned and qualified, but it does **not** yet establish that the full #360 pilot can run on Windows.

A separate adaptation is required before Windows can replace Linux for the credential-backed provider/SSH pilot. Do not weaken Linux labels or silently route the Linux pilot to Windows.

Do not put GitHub tokens, registration tokens, SSH keys, provider credentials, or endpoint values in project execution context, traces, artifacts, PR bodies, or logs.
