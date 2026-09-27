export type MissionStatus = 'ACCEPTED' | 'FAILED' | 'BLOCKED' | 'WAITING_APPROVAL' | 'RUNNING' | 'VERIFYING' | 'CANCELLED';
export type AcceptanceDecision = 'ACCEPT' | 'REVISE' | 'DENY';

export interface Mission { mission_id?: string; objective: string; required_capabilities: string[]; task_family?: string | null; }
export interface AcceptanceBudget {
  money_limit: number; money_used?: number; token_limit: number; tokens_used?: number;
  wall_time_limit_s: number; wall_time_used_s?: number; verifier_attempt_limit: number; verifier_attempts_used?: number;
}
export interface AttemptRecord {
  attempt_number: number; execution_id: string; orchestrator_id: string; execution_status: string | null;
  acceptance_decision: AcceptanceDecision; reasons: string[]; started_at_epoch: number; ended_at_epoch: number;
  failure_class?: string | null; cost: number; tokens?: number;
}
export interface AcceptanceProof { decision: AcceptanceDecision; reasons: string[]; evidence_ids: string[]; digest: string; }
export interface MissionRecord {
  mission_id: string; mission: Mission; status: MissionStatus; revision: number; orchestrator_id?: string | null;
  acceptance_decision: AcceptanceDecision; attempted_orchestrators: string[]; history?: string[]; attempts: AttemptRecord[];
  acceptance?: { decision: AcceptanceDecision; reasons: string[]; proof: AcceptanceProof | null };
  proof?: AcceptanceProof | null;
  budget: AcceptanceBudget; execution?: Record<string, unknown> | null;
  approval_request?: { approval_id: string; execution_id: string; subject_state_id: string; policy_bundle_id: string; reason: string } | null;
  approval_record?: { approval_id: string; approver_id: string; approved: boolean } | null;
}
export interface RuntimeCatalogEntry {
  orchestrator_id: string; version: string; capabilities: string[]; health: string; cost: number; latency_ms: number;
  trust_profile: string; success_rate: number; quality: number; reliability: number; disposition: 'ACTIVE' | 'QUARANTINED';
  quarantine_reason?: string; quarantine_actor?: string; quarantined_at?: number;
}
export interface RuntimeCertification {
  certificate_id: string; orchestrator_id: string; runtime_version: string; probe_execution_id: string; passed: boolean;
  failed_checks: string[]; checks_digest: string; total_checks: number; certified_at_epoch: number; revoked: boolean;
  fresh?: boolean | null; reusable?: boolean; revocation_reason?: string; revocation_actor?: string; revoked_at_epoch?: number;
}
export interface BenchmarkEvidence {
  evidence_id: string; benchmark_id: string; benchmark_version: string; task_set: string; executor_id: string; executor_version: string;
  harness_id: string; harness_version: string; model_id: string; provider_id: string; model_version: string;
  runtime_config_digest: string; tool_policy_digest: string; environment_id: string; observed_at_epoch: number; source: string;
  raw_result_ref: string; metrics: { name: string; value: number; unit: string }[];
}
export interface MissionEvent { event_id: string; mission_id: string; kind: string; timestamp: number; data: Record<string, unknown>; }
export interface DoctorReport {
  overall_status: 'PASS' | 'FAIL'; timestamp?: number;
  checks: { name: string; status: 'PASS' | 'FAIL'; details: string; metrics?: Record<string, unknown> }[];
}
