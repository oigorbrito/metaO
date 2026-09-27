export type MissionStatus = 'ACCEPTED' | 'FAILED' | 'BLOCKED' | 'WAITING_APPROVAL' | 'RUNNING';
export type ExecutionStatus = 'SUCCEEDED' | 'FAILED' | 'CANCELLED' | 'TIMED_OUT';
export type AcceptanceDecision = 'ACCEPT' | 'REVISE' | 'DENY';
export type HealthStatus = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'QUARANTINED';
export type RuntimeDisposition = 'ACTIVE' | 'QUARANTINED';

export interface Mission {
  mission_id: string;
  objective: string;
  required_capabilities: string[];
  task_family?: string | null;
}

export interface Policy {
  policy_bundle_id: string;
  allowed: boolean;
  require_human: boolean;
  reason?: string;
}

export interface AcceptanceBudget {
  money_limit: number;
  token_limit: number;
  wall_time_limit_s: number;
  verifier_attempt_limit: number;
}

export interface AcceptanceContext {
  subject_id: string;
  subject_state_id: string;
  verification_context_id: string;
  policy_bundle_id: string;
  required_obligations: string[];
  trusted_verifiers: string[];
  trusted_provenance_roots: string[];
  authorized_authorities: string[];
}

export interface AcceptanceProof {
  proof_id: string;
  obligation_results: Record<string, { passed: boolean; verifier: string; timestamp: number; details?: string }>;
  signature: string;
  accepted_at: number;
  authority_id: string;
}

export interface AttemptRecord {
  attempt_number: number;
  execution_id: string;
  orchestrator_id: string;
  execution_status: ExecutionStatus | null;
  acceptance_decision: AcceptanceDecision;
  reasons: string[];
  started_at_epoch: number;
  ended_at_epoch: number;
  cost: number;
  tokens: number;
}

export interface MissionRecord {
  mission_id: string;
  mission: Mission;
  policy: Policy;
  budget: AcceptanceBudget;
  acceptance_context: AcceptanceContext;
  status: MissionStatus;
  revision: number;
  created_at: number;
  updated_at: number;
  orchestrator_id?: string;
  acceptance_decision: AcceptanceDecision;
  attempted_orchestrators: string[];
  attempts: AttemptRecord[];
  proof?: AcceptanceProof;
  output?: any;
  approval_request?: {
    required: boolean;
    approved?: boolean;
    approver_id?: string;
    decided_at?: number;
    reason?: string;
  };
}

export interface RuntimeCatalogEntry {
  orchestrator_id: string;
  version: string;
  capabilities: string[];
  health: HealthStatus;
  cost: number;
  latency_ms: number;
  trust_profile: string;
  success_rate: number;
  quality: number;
  reliability: number;
  disposition: RuntimeDisposition;
  quarantine_reason?: string;
  quarantine_actor?: string;
  quarantined_at?: number;
}

export interface RuntimeCertification {
  certificate_id: string;
  orchestrator_id: string;
  runtime_version: string;
  probe_execution_id: string;
  passed: boolean;
  failed_checks: string[];
  checks_digest: string;
  total_checks: number;
  certified_at_epoch: number;
  revoked: boolean;
  revocation_reason?: string;
  revocation_actor?: string;
  revoked_at_epoch?: number;
}

export interface BenchmarkEvidence {
  evidence_id: string;
  benchmark_id: string;
  benchmark_version: string;
  task_set: string;
  executor_id: string;
  executor_version: string;
  harness_id: string;
  harness_version: string;
  model_id: string;
  provider_id: string;
  model_version: string;
  runtime_config_digest: string;
  tool_policy_digest: string;
  environment_id: string;
  observed_at_epoch: number;
  source: string;
  raw_result_ref: string;
  metrics: {
    name: string;
    value: number;
    unit: string;
  }[];
}

export interface MissionEvent {
  event_id: string;
  mission_id: string;
  kind: string;
  timestamp: number;
  data: Record<string, any>;
}

export interface DoctorReport {
  overall_status: 'PASS' | 'FAIL';
  timestamp: number;
  checks: {
    name: string;
    status: 'PASS' | 'FAIL';
    details: string;
    metrics?: Record<string, any>;
  }[];
}
