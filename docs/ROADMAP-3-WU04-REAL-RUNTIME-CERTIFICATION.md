# Roadmap 3 WU04 — Real Runtime Certification Regression V1

## Objective

Prove that the Roadmap 3 conformance, admission, and durable-certification
boundary applies unchanged to the two real orchestrator SDKs already proven in
Roadmap 2:

- LangGraph 1.2.11;
- CrewAI 1.15.16.

WU04 does not add a third framework. It validates that the generic certification
path is not merely a fake-runtime/unit-test abstraction.

## Evidence shape

For each real runtime:

```text
real SDK object
  -> existing thin metaO adapter
  -> WU01 active conformance probe
  -> WU03 deterministic certificate
  -> WU02 operational admission
  -> common OrchestratorRegistry / OrchestratorCatalog
```

The same `RuntimeAdmissionGate` and certification store are used for both
frameworks. There is no framework-specific branch in the admission or
certification code.

## CrewAI sandbox rule

CrewAI uses a deterministic local `BaseLLM` implementation so the real CrewAI
runtime, Agent, Task, Crew, and Process code execute without paid model-provider
keys.

This proves real CrewAI SDK/runtime compatibility with the certification
boundary. It does not claim external provider/model behavior.

## LangGraph sandbox rule

LangGraph uses a real compiled `StateGraph` with a deterministic local node. No
external model/service is required.

## Required evidence

1. installed LangGraph version is exactly 1.2.11;
2. installed CrewAI version is exactly 1.15.16;
3. real LangGraph adapter passes conformance, is certified, and is admitted;
4. real CrewAI adapter passes conformance, is certified, and is admitted;
5. CrewAI real runtime actually invokes the deterministic BaseLLM;
6. both real frameworks coexist behind one registry/catalog/certification boundary;
7. Roadmap 2 real-runtime integration regression remains green when executable CI is available;
8. WU01-WU03 and the full historical unit suite remain green when executable CI is available;
9. SDK imports remain confined to adapters/tests, not Roadmap 3 Core-neutral modules.

## Non-goals

WU04 does not claim:

- external OpenAI/Anthropic/Gemini provider execution;
- production latency or throughput;
- a third orchestrator runtime;
- runtime-factory auto-admission;
- learned routing;
- production certification or security accreditation.

## Gate

```text
REAL_LANGGRAPH_CERTIFICATION = PASS
REAL_CREWAI_CERTIFICATION = PASS
PINNED_LANGGRAPH = 1.2.11
PINNED_CREWAI = 1.15.16
SHARED_CERTIFICATION_BOUNDARY = YES
THIRD_FRAMEWORK_ADDED = NO
EXTERNAL_PROVIDER_CLAIM = NO
SDK_NEUTRAL_CORE = YES
FULL_REGRESSION = GREEN
```

`PASS`/`GREEN` may only be claimed after the integration test actually executes.
A hosted-runner failure before the first step is not runtime evidence.
