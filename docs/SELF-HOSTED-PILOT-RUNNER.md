# Self-Hosted Runner for the #360 Operational Pilot

This runner exists only to execute the dedicated workflow for the #360 multi-provider project pilot while the hosted-runner blocker #71 remains active.

## Required runner identity

Register the runner with all of these labels:

- `self-hosted`
- `linux`
- `x64`
- `metao-project-pilot`

The `metao-project-pilot` label is an execution boundary. Do not satisfy the workflow by retargeting an arbitrary shared self-hosted runner.

## Machine readiness

On the candidate Linux x64 machine, check out the exact repository head and run:

```bash
python3 scripts/self_hosted_runner_readiness.py
```

A readiness PASS means only that the local machine has the minimum tool surface required by the pilot workflow. It does not check repository secrets, provider credentials, remote SSH hosts, or project acceptance, and it is not an operational PASS.

Required local tools:

- Python 3.12+
- Git
- OpenSSH client (`ssh`, `scp`)
- `curl`
- `tar`
- writable temporary storage

The machine also needs outbound HTTPS access for GitHub, Python package installation, OpenAI, and Gemini, plus network reachability to the two configured SSH executor hosts.

## Runner installation and registration

Runner installation and registration are administrative operations and require a short-lived registration token. Do not commit or paste that token into repository files, issues, workflow inputs, or logs.

Use GitHub's repository UI for the canonical, current commands:

1. Open repository **Settings → Actions → Runners**.
2. Choose **New self-hosted runner**.
3. Select **Linux** and **x64**.
4. On the runner machine, execute the download/install commands GitHub shows for the current runner release.
5. Execute the generated `config.sh` registration command, adding the dedicated custom label `metao-project-pilot` while preserving the default self-hosted/Linux/x64 labels.
6. Install/start the runner as a service using the service commands shown by the runner package for that machine.
7. Confirm the runner is online and that the repository UI shows the `metao-project-pilot` label.

Do not store the registration token after registration. If registration fails or the token expires, obtain a new token through the administrative UI.

## Pilot configuration

After the runner is online, configure the repository secrets listed in `docs/PROJECT-MULTI-PROVIDER-PILOT-RUNBOOK.md`. The two SSH endpoints must be distinct and must allow the configured users to create/delete disposable `/tmp/metao-project-pilot.*` directories.

Then manually dispatch:

`Project Multi-Provider Supervision Pilot Self-Hosted`

with authorization:

`I_AUTHORIZE_METAO_MULTI_PROVIDER_PROJECT_PILOT`

The workflow runs the no-provider-call preflight first. Provider-backed execution must not start if preflight fails.

## Evidence boundary

Runner readiness PASS means:

```text
RUNNER_MACHINE_READINESS = PASS
RUNNER_REGISTRATION = NOT_ESTABLISHED_BY_READINESS
REPOSITORY_SECRETS = NOT_CHECKED
SSH_ENDPOINT_PREFLIGHT = NOT_RUN
PROVIDER_EXECUTION = NOT_RUN
#360_OPERATIONAL_PASS = NO
```

Only the exact-head self-hosted pilot run can establish #360 operational PASS.