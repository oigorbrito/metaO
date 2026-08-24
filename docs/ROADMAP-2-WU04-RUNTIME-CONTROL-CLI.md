# Roadmap 2 WU04 — Runtime Control CLI V1

## Objective

Expose the durable runtime controls from WU03 through the installed `metao`
console command without rewriting or weakening the Roadmap 1 mission CLI.

## Compatibility strategy

`metao.cli` remains the authoritative implementation for existing mission
commands. The packaged console script now points to `metao.entrypoint:main`, a
thin wrapper that:

1. intercepts runtime-control commands only;
2. delegates every existing mission command to `metao.cli.main` unchanged;
3. uses the same `--db` for runtime controls by default;
4. preserves `METAO_RUNTIME_CONTROL_DB` as an explicit override.

This means a durable quarantine recorded with:

```text
metao --db .metao/metao.db runtime-quarantine crewai \
  --reason "operator investigation" --actor igor
```

is automatically seen by a later generic-factory mission invocation using the
same database:

```text
metao --db .metao/metao.db run mission.json \
  --factory metao.runtime_factory:create_operator
```

No duplicate runtime-control database configuration is required.

## Commands

```text
metao runtimes --factory module:function
metao runtime-quarantine <orchestrator_id> --reason <text> --actor <id>
metao runtime-restore <orchestrator_id> --reason <text> --actor <id>
metao runtime-history <orchestrator_id>
```

All commands accept the existing global `--db` option.

### `runtimes`

Requires a factory whose operator exposes the read-only `runtime_entries()`
surface. The declarative factory from WU02 now returns
`RuntimeCatalogOperator`, a `MissionOperator` subclass providing that surface.

The output is deterministic machine-readable JSON containing:

- orchestrator id and version;
- capabilities;
- governed health, including `quarantined`;
- cost and latency;
- trust profile;
- success-rate, quality and reliability routing metadata.

Listing runtimes does not execute a runtime.

### Quarantine / restore / history

These commands write/read `SQLiteRuntimeControlStore` directly. Each mutation is
revisioned and records reason, actor and timestamp. History is append-only.

## Fail-closed rules

- empty reason/actor or invalid timestamps are rejected;
- `runtimes` rejects factories without a runtime-catalog surface;
- runtime-control database corruption is surfaced as an error;
- legacy mission commands continue using their existing structured error model;
- no orchestrator SDK is imported by the entrypoint or runtime factory.

## Required evidence

1. installed console help preserves Roadmap 1 commands and adds runtime commands;
2. quarantine is durable and machine-readable;
3. `runtimes` reflects quarantine without runtime execution;
4. restore reflects live health and preserves history;
5. a legacy `run` automatically honors quarantine from the same SQLite DB;
6. legacy read commands still delegate unchanged;
7. unseen runtime history is an empty read-only result;
8. invalid runtime-control input fails closed;
9. incompatible factories fail closed for `runtimes`;
10. entrypoint/factory remain SDK-neutral;
11. complete historical unit suite remains green;
12. real LangGraph/CrewAI and Block O regressions remain green.

## Gate

```text
RUNTIME_CONTROL_CLI = PASS
LEGACY_MISSION_CLI_REGRESSION = PASS
QUARANTINE_AFFECTS_NEXT_RUN = YES
RUNTIME_LIST_EXECUTES_RUNTIME = NO
SDK_NEUTRAL = YES
FULL_REGRESSION = GREEN
```
