#!/usr/bin/env bash
set -euo pipefail

REPO="${METAO_GITHUB_REPOSITORY:-oigorbrito/metaO}"
WORKFLOW="self-hosted-runner-readiness-bridge.yml"
TARGET_HEAD="${1:-${METAO_TARGET_HEAD:-}}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$REPO" == "oigorbrito/metaO" ]] || fail "METAO_GITHUB_REPOSITORY must be exactly oigorbrito/metaO"
[[ "$TARGET_HEAD" =~ ^[0-9a-fA-F]{40}$ ]] || fail "provide an exact 40-character target commit SHA"
TARGET_HEAD="${TARGET_HEAD,,}"

command -v gh >/dev/null 2>&1 || fail "gh CLI is required"
gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated"

gh api "repos/${REPO}/commits/${TARGET_HEAD}" --silent >/dev/null || fail "target SHA is not readable in ${REPO}"

gh workflow run "$WORKFLOW" \
  --repo "$REPO" \
  --ref main \
  --field "target_head=${TARGET_HEAD}"

printf '{"dispatch":"SUBMITTED","repository":"%s","workflow":"%s","workflow_ref":"main","target_head":"%s","runner_readiness":"NOT_RUN","pilot_operational_pass":false}\n' \
  "$REPO" "$WORKFLOW" "$TARGET_HEAD"

printf 'Observe with: gh run list --repo %q --workflow %q --event workflow_dispatch --limit 5\n' "$REPO" "$WORKFLOW" >&2
