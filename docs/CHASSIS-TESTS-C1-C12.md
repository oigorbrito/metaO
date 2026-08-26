# metaO Chassis Conformance Tests — C1–C12

Owner: #189

1. C1 Core purity: generic Core contains no framework/vendor SDK types.
2. C2 Whole-orchestrator replacement: equivalent mission can swap materially different orchestrators without Core/policy/evidence/acceptance changes.
3. C3 Adapter registration lifecycle: register/unregister/re-register without mutating Core definitions.
4. C4 Contract versioning: incompatible adapter versions fail explicitly.
5. C5 Failure containment: adapter crash/timeout never becomes success/accepted and cannot corrupt peer runtime state.
6. C6 Reconciliation idempotency: repeated state reconciliation converges without duplicate effects.
7. C7 Desired vs observed separation: declarations do not self-certify observed health/capability.
8. C8 Extension authority boundary: plugin/provider outputs cannot mint acceptance authority.
9. C9 Durable boundary: no second durable workflow engine is introduced alongside Conductor.
10. C10 Optional-dependency discipline: Core imports/tests pass without optional runtime SDK dependencies.
11. C11 Plugin-discovery determinism: duplicate IDs/version conflicts/load ambiguity fail deterministically.
12. C12 Out-of-process seam: OrchestratorContract semantics can cross an RPC/component boundary without changing domain objects.

Evidence levels:

```text
C*_L0 = architecture inspection
C*_L1 = source/import boundary inspection
C*_L2 = focused executable test
C*_L3 = integration with 2 runtimes
C*_L4 = process/crash/restart isolation
```

No chassis change is authorized from L0/L1 alone.