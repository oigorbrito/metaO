#!/usr/bin/env bash
set -euo pipefail

REPO="${METAO_GITHUB_REPOSITORY:-oigorbrito/metaO}"
RUNNER_LABEL="metao-project-pilot"
RUNNER_NAME="${METAO_RUNNER_NAME:-metao-project-pilot-$(hostname -s)}"
INSTALL_DIR="${METAO_RUNNER_INSTALL_DIR:-${HOME}/actions-runner-metao-project-pilot}"
RUNNER_VERSION="${METAO_ACTIONS_RUNNER_VERSION:-v2.337.0}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

[[ "$REPO" == "oigorbrito/metaO" ]] || fail "METAO_GITHUB_REPOSITORY must be exactly oigorbrito/metaO"
[[ "$(uname -s)" == "Linux" ]] || fail "runner host must be Linux"
case "$(uname -m)" in
  x86_64|amd64) ;;
  *) fail "runner host must be x64" ;;
esac
[[ "$RUNNER_NAME" =~ ^[A-Za-z0-9._-]+$ ]] || fail "METAO_RUNNER_NAME contains unsupported characters"
[[ "$RUNNER_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "METAO_ACTIONS_RUNNER_VERSION must be an exact vMAJOR.MINOR.PATCH tag"
[[ "$INSTALL_DIR" = /* ]] || fail "METAO_RUNNER_INSTALL_DIR must be absolute"

for command_name in gh curl tar sha256sum git ssh scp python3 sudo; do
  require_command "$command_name"
done

gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated; run gh auth login first"

python3 - <<'PY' || fail "Python 3.12+ is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

remote_runner_json="$(gh api --paginate "repos/${REPO}/actions/runners" --jq \
  ".runners[] | select(.name == \"${RUNNER_NAME}\") | {id,name,status,busy,labels:[.labels[].name]}" 2>/dev/null || true)"

if [[ -f "${INSTALL_DIR}/.runner" ]]; then
  [[ -x "${INSTALL_DIR}/svc.sh" ]] || fail "local runner is configured but svc.sh is missing"
  [[ -n "$remote_runner_json" ]] || fail "local runner is configured but no matching GitHub runner registration exists"
  REMOTE_RUNNER_JSON="$remote_runner_json" RUNNER_LABEL="$RUNNER_LABEL" python3 - <<'PY' || fail "registered runner is missing required labels"
import json
import os
runner = json.loads(os.environ["REMOTE_RUNNER_JSON"])
labels = {label.lower() for label in runner.get("labels", [])}
required = {"self-hosted", "linux", "x64", os.environ["RUNNER_LABEL"].lower()}
raise SystemExit(1 if required - labels else 0)
PY
  sudo "${INSTALL_DIR}/svc.sh" start >/dev/null
  printf '{"installer":"PASS","repository":"%s","runner_name":"%s","runner_label":"%s","runner_version":"%s","already_configured":true,"registration_mode":"existing-match","registration_token_emitted":false,"credentials_emitted":false,"pilot_operational_pass":false}\n' \
    "$REPO" "$RUNNER_NAME" "$RUNNER_LABEL" "$RUNNER_VERSION"
  exit 0
fi

[[ -z "$remote_runner_json" ]] || fail "a GitHub runner named ${RUNNER_NAME} already exists but this install directory is not configured"

mkdir -p "$INSTALL_DIR"
[[ -w "$INSTALL_DIR" ]] || fail "install directory is not writable: ${INSTALL_DIR}"
[[ -z "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]] || fail "install directory must be empty for first installation"

release_json="$(gh api "repos/actions/runner/releases/tags/${RUNNER_VERSION}")"
asset_json="$(RELEASE_JSON="$release_json" RUNNER_VERSION="$RUNNER_VERSION" python3 - <<'PY'
import json
import os
release = json.loads(os.environ["RELEASE_JSON"])
if release.get("tag_name") != os.environ["RUNNER_VERSION"]:
    raise SystemExit("runner release tag does not match requested version")
assets = [a for a in release.get("assets", []) if a.get("name", "").endswith("linux-x64-" + os.environ["RUNNER_VERSION"].removeprefix("v") + ".tar.gz")]
if len(assets) != 1:
    raise SystemExit("expected exactly one linux-x64 runner asset for requested version")
asset = assets[0]
digest = asset.get("digest") or ""
if not digest.startswith("sha256:"):
    raise SystemExit("runner release asset does not expose a sha256 digest")
print(json.dumps({"name": asset["name"], "url": asset["browser_download_url"], "sha256": digest.split(":", 1)[1]}))
PY
)"

asset_name="$(ASSET_JSON="$asset_json" python3 -c 'import json,os; print(json.loads(os.environ["ASSET_JSON"])["name"])')"
asset_url="$(ASSET_JSON="$asset_json" python3 -c 'import json,os; print(json.loads(os.environ["ASSET_JSON"])["url"])')"
asset_sha256="$(ASSET_JSON="$asset_json" python3 -c 'import json,os; print(json.loads(os.environ["ASSET_JSON"])["sha256"])')"

tmp_dir="$(mktemp -d -t metao-actions-runner.XXXXXX)"
cleanup() {
  unset registration_token || true
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

archive="${tmp_dir}/${asset_name}"
curl --fail --location --silent --show-error "$asset_url" --output "$archive"
printf '%s  %s\n' "$asset_sha256" "$archive" | sha256sum --check --status || fail "GitHub Actions runner archive checksum verification failed"
tar -xzf "$archive" -C "$INSTALL_DIR"

[[ -x "${INSTALL_DIR}/config.sh" ]] || fail "runner archive did not provide config.sh"
[[ -x "${INSTALL_DIR}/svc.sh" ]] || fail "runner archive did not provide svc.sh"

registration_token="$(gh api --method POST "repos/${REPO}/actions/runners/registration-token" --jq .token)"
[[ -n "$registration_token" ]] || fail "GitHub did not return a runner registration token"

(
  cd "$INSTALL_DIR"
  ./config.sh \
    --unattended \
    --url "https://github.com/${REPO}" \
    --token "$registration_token" \
    --name "$RUNNER_NAME" \
    --labels "$RUNNER_LABEL" \
    --work _work
)
unset registration_token

[[ -f "${INSTALL_DIR}/.runner" ]] || fail "runner configuration did not create .runner"

sudo "${INSTALL_DIR}/svc.sh" install "$(id -un)" >/dev/null
sudo "${INSTALL_DIR}/svc.sh" start >/dev/null

registered_json="$(gh api --paginate "repos/${REPO}/actions/runners" --jq \
  ".runners[] | select(.name == \"${RUNNER_NAME}\") | {id,name,status,busy,labels:[.labels[].name]}" 2>/dev/null || true)"
[[ -n "$registered_json" ]] || fail "runner configuration completed but GitHub registry does not show the runner"
REMOTE_RUNNER_JSON="$registered_json" RUNNER_LABEL="$RUNNER_LABEL" python3 - <<'PY' || fail "new runner registration is missing required labels"
import json
import os
runner = json.loads(os.environ["REMOTE_RUNNER_JSON"])
labels = {label.lower() for label in runner.get("labels", [])}
required = {"self-hosted", "linux", "x64", os.environ["RUNNER_LABEL"].lower()}
raise SystemExit(1 if required - labels else 0)
PY

printf '{"installer":"PASS","repository":"%s","runner_name":"%s","runner_label":"%s","runner_version":"%s","runner_asset_sha256":"%s","already_configured":false,"registration_mode":"first-install-no-replace","registration_token_emitted":false,"credentials_emitted":false,"pilot_operational_pass":false}\n' \
  "$REPO" "$RUNNER_NAME" "$RUNNER_LABEL" "$RUNNER_VERSION" "$asset_sha256"
