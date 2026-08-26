# Provisional Chassis Decision

```text
KEEP_CURRENT_METAO_PYTHON_CHASSIS = YES
WHOLE_EXTERNAL_CHASSIS_ADOPTION = NO
SEARCH_FOUND_USEFUL_HARDENING_DONORS = YES
```

Primary hardening donors:

1. Crossplane — generic control-plane extension/core purity/conformance.
2. controller-runtime — desired-vs-observed reconciliation and idempotent convergence.
3. agent-hooks — framework-neutral lifecycle control surface and CTK.
4. pluggy — conditional Python plugin registry if dynamic discovery becomes necessary.
5. WASM Component Model — deferred future typed isolation boundary.

No implementation change is authorized until #189 closes C1–C12 with evidence.