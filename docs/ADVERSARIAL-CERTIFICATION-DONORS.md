# Adversarial certification donor pins (#162)

This file records **evaluation references**, not product runtime dependencies and not a safety certification.

The machine-readable source of truth is:

`docs/adversarial-certification-donors.json`

Validate it with:

```console
python scripts/validate_adversarial_certification_donors.py
```

## Pinned AgentDojo reference

- package: `agentdojo==0.1.35`
- tag: `v0.1.35`
- release commit: `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b`
- inspected benchmark boundary:
  - `src/agentdojo/benchmark.py`
  - `src/agentdojo/attacks/`
  - `src/agentdojo/task_suite/`
  - `src/agentdojo/functions_runtime.py`
- paper: *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents* (NeurIPS 2024 Datasets and Benchmarks Track)

AgentDojo reports utility and security separately. A donor-side transport/API/evaluator failure must not be normalized as a metaO security PASS merely because no forbidden action was observed.

## Pinned PyRIT reference

- package: `pyrit==1.1.0`
- tag: `v1.1.0`
- release page commit prefix: `d0524f0`
- inspected framework boundary:
  - `doc/code/framework.md`
  - `doc/scanner/1_pyrit_scan.py`
  - `pyrit/score/scorer.py`
  - `pyrit/executor/attack/core/attack_strategy.py`
- paper/DOI: *PyRIT: Democratizing AI Red Teaming Through Open-Source Tooling*, `10.48550/arXiv.2410.02828`

PyRIT 1.1.0 supports an undetermined score/outcome state. For a forbidden-objective security campaign, attack success means the security category failed. Undetermined/evaluator error remains `Unknown`/`EvaluatorError`, never PASS.

## metaO normalization boundary

The canonical contract already exists in:

`experiments/rust-chassis-a/metao-contracts/src/runtime_certification.rs`

Allowed category states are:

```text
Pass
Fail
Skipped
NotRequested
Unknown
EvaluatorError
```

Required categories with `Skipped`, `NotRequested`, `Unknown`, `EvaluatorError`, or no result project to `Incomplete`. A report is not certified solely because the attack framework did not produce a successful attack.

## Evidence classification

```text
DONOR_PINS = IMPLEMENTED
ADVERSARIAL_CAMPAIGN = NOT_RUN
TWO_REAL_RUNTIME_ADAPTERS = NOT_PROVEN
UNIVERSAL_SAFETY_CLAIM = NOT_AUTHORIZED
```

Running AgentDojo/PyRIT against real or credential-backed runtimes remains separate external evidence work and requires the controlled environment described in #162.
