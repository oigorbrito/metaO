# Chassis Search Notes — 2026-08-26

Additional projects reviewed during the chassis-specific sweep:

- `crossplane/crossplane` — strongest mature generic-control-plane architecture reference; keep semantic patterns, not runtime dependency.
- `kcp-dev/kcp` — useful isolated-workspace/API-provider reference; too Kubernetes-heavy for literal metaO Core.
- `kubernetes-sigs/controller-runtime` — strong reconcile-loop semantics; Kubernetes-specific implementation should not enter metaO Core.
- `pytest-dev/pluggy` — mature Python plugin manager and hookspec system; evaluate only when dynamic plugin discovery/multi-implementation hooks are required.
- `WebAssembly/component-model` — future typed component/isolation seam; defer literal adoption.
- `smartcomputer-ai/agent-os` — valuable minimal-trusted-base/effect/receipt/replay concepts; reject as whole chassis because it brings its own world/AIR/workflow model.
- `isaacsight/agent-os` — interesting permissions/namespaces/quota/taint concepts but small/alpha and not suitable as a chassis dependency.
- `xraph/ctrlplane` — composable generic Go control-plane library; useful comparison, but current fit is lower than Crossplane/controller-runtime and language mismatch is high.
- `openclarity/simple-controller-runtime` — compact non-Kubernetes-capable reconciliation reference; useful for test-fixture inspiration if controller-runtime semantics prove too Kubernetes-specific.

Search outcome:

```text
NO_EXTERNAL_CHASSIS_CLEARLY_SUPERSEDES_METAO_CURRENT_CORE = TRUE
BEST_PATH = KEEP + HARDEN CURRENT PYTHON CORE
```
