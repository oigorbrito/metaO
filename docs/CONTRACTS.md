# Arkx Architectural Contracts

This document defines the authoritative data contracts for the Arkx (metaO) system. Adherence to these contracts is mandatory for all Executor Adapters and Evidence Normalizers to ensure framework-neutral acceptance.

## 1. The Evidence Contract

The core of Arkx's trust model is the `EvidenceEnvelope`. An executor does not "declare" success; it provides evidence that is independently verified.

### 1.1 EvidenceEnvelope Anatomy

| Field | Type | Requirement | Source of Truth | Description |
| :--- | :--- | :--- | :--- | :--- |
| `evidence_id` | `str` | Mandatory | Verifier | Unique identifier for this specific piece of evidence. |
| `obligation_id` | `str` | Mandatory | Policy | The specific requirement (obligation) this evidence satisfies. |
| `mission_id` | `str` | Mandatory | Mission | Must match the mission being executed. |
| `execution_id` | `str` | Mandatory | Control Plane | Must match the specific execution attempt. |
| `adapter_id` | `str` | Mandatory | Registry | ID of the adapter that produced the evidence. |
| `adapter_version`| `str` | Mandatory | Registry | Version of the adapter (for reproducibility). |
| `attempt_id` | `str` | Mandatory | Control Plane | The specific attempt within the execution. |
| `payload_digest` | `str` | Mandatory | Hash | SHA-256 hash of the raw evidence payload. |
| `provenance` | `str` | Mandatory | Verifier | Cryptographic or traceable root of the evidence origin. |
| `verifier_id` | `str` | Mandatory | Verifier | The authority that verified the payload. |
| `passed` | `bool` | Mandatory | Verifier | Final binary decision on the evidence quality. |

### 1.2 The Normalization Process

Every `ExecutorAdapter` must be paired with an `EvidenceNormalizer`. The normalizer's sole responsibility is to transform raw executor output into one or more `EvidenceEnvelopes`.

**Normalization Invariants:**
- **No Inference:** Normalizers must not "guess" success. If a field is missing from the raw output, the envelope must fail to be created or mark `passed=False`.
- **Immutable Bindings:** The `execution_id` and `mission_id` must be passed from the `ExecutionRequest` to the envelope without modification.
- **Payload Integrity:** The `payload_digest` must be calculated over the raw, un-normalized data to allow for future audits.

## 2. Binding & Acceptance Gates

The `acceptance` module applies strict gates to every envelope. If any gate fails, the decision is `BLOCK`.

### 2.1 Binding Gate
Evidence is rejected if:
- `mission_id` $\neq$ Current Mission.
- `execution_id` $\neq$ Current Execution.
- `adapter_version` $\neq$ The version registered in the catalog.

### 2.2 Freshness Gate
Evidence has a TTL (Time-to-Live). Stale evidence leads to `AcceptanceDecision.STALE`.

### 2.3 Conflict Gate
- **Duplicate IDs:** Two envelopes with the same `evidence_id` $\rightarrow$ `BLOCK`.
- **Conflicting Obligations:** Two different evidence pieces for the same `obligation_id` $\rightarrow$ `BLOCK`.

## 3. Failure Taxonomy for Normalizers

When a normalizer cannot produce a valid envelope, it should not simply return `None`. It must raise a `NormalizationError` (or return a failed envelope) categorized by:
- `STRUCTURAL_INVALIDITY`: The raw output is not in the expected format.
- `MISSING_BINDING`: The output lacks the necessary IDs to bind it to a mission.
- `UNTRUSTED_SOURCE`: The provenance root is not recognized.
