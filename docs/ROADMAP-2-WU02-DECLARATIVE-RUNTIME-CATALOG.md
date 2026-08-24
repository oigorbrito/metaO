# Roadmap 2 WU02 — Declarative Runtime Catalog V1

## Objective

Make the multi-runtime architecture operational from the existing CLI without
requiring each deployment to hand-write a custom `MissionOperator` factory.

The existing CLI factory boundary remains unchanged:

```text
metao run mission.json --factory metao.runtime_factory:create_operator
```

The generic factory reads a trusted local manifest path from:

```text
METAO_RUNTIME_CATALOG=/path/to/runtimes.json
```

## Architectural rule

The manifest never names framework SDK classes. It names trusted local plugin
factories using `module:function` syntax. Each plugin returns:

```python
RuntimePlugin(
    orchestrator=<OrchestratorContract>,
    normalizer=<EvidenceNormalizer>,
)
```

A LangGraph plugin may import LangGraph. A CrewAI plugin may import CrewAI.
`metao.runtime_factory`, the CLI and Core do not.

## Manifest shape

```json
{
  "runtimes": [
    {
      "factory": "my_runtime_plugins:build_langgraph",
      "cost": 0.05,
      "latency_ms": 250,
      "success_rate": 0.98,
      "quality": 0.95,
      "reliability": 0.97,
      "trust_profile": "local"
    },
    {
      "factory": "my_runtime_plugins:build_crewai",
      "cost": 0.08,
      "latency_ms": 400,
      "success_rate": 0.96,
      "quality": 0.94,
      "reliability": 0.95,
      "trust_profile": "local"
    }
  ]
}
```

## Trust boundary

Plugin factories are executable Python code. The manifest must therefore be
considered trusted operator configuration, equivalent to the existing explicit
`--factory module:function` hook. WU02 does not claim sandboxing of plugin code.

Malformed manifests, invalid routing metrics, missing factories and invalid
plugin return types fail closed before a mission runs.

## Required evidence

1. a manifest builds a multi-runtime `MissionOperator`;
2. strategy selects the stronger declared runtime;
3. failed declared runtime can fail over to another declared runtime;
4. `METAO_RUNTIME_CATALOG` factory is CLI-compatible;
5. `metao run` executes through the generic factory without a custom operator factory;
6. missing/invalid configuration fails closed;
7. invalid routing profiles fail closed;
8. the factory module contains no LangGraph/CrewAI imports.

## Gate

```text
DECLARATIVE_RUNTIME_CATALOG = PASS
CUSTOM_OPERATOR_FACTORY_REQUIRED = NO
CORE_SDK_LEAK = NO
ROADMAP_1_REGRESSION = 144/144 PASS
```
