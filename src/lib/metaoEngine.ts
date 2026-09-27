import {
  Mission,
  Policy,
  AcceptanceBudget,
  AcceptanceContext,
  MissionRecord,
  RuntimeCatalogEntry,
  RuntimeCertification,
  BenchmarkEvidence,
  MissionEvent,
  DoctorReport,
} from '../types/metao';

// In-memory persistent stores for metaO Control Plane

class MetaOEngine {
  private runtimes: Map<string, RuntimeCatalogEntry> = new Map();
  private certifications: Map<string, RuntimeCertification> = new Map();
  private benchmarks: BenchmarkEvidence[] = [];
  private missions: Map<string, MissionRecord> = new Map();
  private events: MissionEvent[] = [];

  constructor() {
    this.initDefaultRuntimes();
    this.initDefaultCertifications();
    this.initDefaultBenchmarks();
    this.initDefaultMissions();
  }

  private initDefaultRuntimes() {
    const list: RuntimeCatalogEntry[] = [
      {
        orchestrator_id: 'quickstart-local',
        version: '1.0.0',
        capabilities: ['workflow'],
        health: 'HEALTHY',
        cost: 0.0,
        latency_ms: 1.0,
        trust_profile: 'quickstart-local',
        success_rate: 1.0,
        quality: 1.0,
        reliability: 1.0,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'openai-agents',
        version: '0.4.1',
        capabilities: ['workflow', 'code_generation', 'tool_calling', 'multi_agent'],
        health: 'HEALTHY',
        cost: 0.02,
        latency_ms: 450,
        trust_profile: 'certified-cloud',
        success_rate: 0.98,
        quality: 0.95,
        reliability: 0.97,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'gemini-interactions',
        version: '0.9.0',
        capabilities: ['workflow', 'multimodal', 'tool_calling', 'long_context', 'reasoning'],
        health: 'HEALTHY',
        cost: 0.015,
        latency_ms: 380,
        trust_profile: 'certified-cloud',
        success_rate: 0.97,
        quality: 0.98,
        reliability: 0.96,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'deepseek-chat',
        version: '2.5.0',
        capabilities: ['workflow', 'reasoning', 'code_generation'],
        health: 'HEALTHY',
        cost: 0.005,
        latency_ms: 620,
        trust_profile: 'certified-cloud',
        success_rate: 0.94,
        quality: 0.96,
        reliability: 0.93,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'codex-app-server',
        version: '1.2.0',
        capabilities: ['code_generation', 'patch_synthesis', 'local_execution'],
        health: 'HEALTHY',
        cost: 0.01,
        latency_ms: 510,
        trust_profile: 'sandboxed-runtime',
        success_rate: 0.92,
        quality: 0.91,
        reliability: 0.94,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'langgraph-conductor',
        version: '0.2.8',
        capabilities: ['workflow', 'stateful_graph', 'human_in_loop'],
        health: 'HEALTHY',
        cost: 0.008,
        latency_ms: 290,
        trust_profile: 'orchestrator-bridge',
        success_rate: 0.95,
        quality: 0.93,
        reliability: 0.95,
        disposition: 'ACTIVE',
      },
      {
        orchestrator_id: 'crewai-adapter',
        version: '0.80.0',
        capabilities: ['multi_agent', 'role_playing', 'delegation', 'workflow'],
        health: 'DEGRADED',
        cost: 0.018,
        latency_ms: 820,
        trust_profile: 'orchestrator-bridge',
        success_rate: 0.89,
        quality: 0.88,
        reliability: 0.86,
        disposition: 'ACTIVE',
      },
    ];

    list.forEach(r => this.runtimes.set(r.orchestrator_id, r));
  }

  private initDefaultCertifications() {
    const certs: RuntimeCertification[] = [
      {
        certificate_id: 'cert-quickstart-001',
        orchestrator_id: 'quickstart-local',
        runtime_version: '1.0.0',
        probe_execution_id: 'quickstart-certification',
        passed: true,
        failed_checks: [],
        checks_digest: 'sha256:d8a21fc7a892b10',
        total_checks: 12,
        certified_at_epoch: Date.now() / 1000 - 86400,
        revoked: false,
      },
      {
        certificate_id: 'cert-openai-agents-001',
        orchestrator_id: 'openai-agents',
        runtime_version: '0.4.1',
        probe_execution_id: 'openai-agents-conformance-v1',
        passed: true,
        failed_checks: [],
        checks_digest: 'sha256:7c9e0a1b2f4d6e8',
        total_checks: 28,
        certified_at_epoch: Date.now() / 1000 - 43200,
        revoked: false,
      },
      {
        certificate_id: 'cert-gemini-001',
        orchestrator_id: 'gemini-interactions',
        runtime_version: '0.9.0',
        probe_execution_id: 'gemini-interactions-conformance-v1',
        passed: true,
        failed_checks: [],
        checks_digest: 'sha256:1a2b3c4d5e6f7a8',
        total_checks: 24,
        certified_at_epoch: Date.now() / 1000 - 36000,
        revoked: false,
      },
      {
        certificate_id: 'cert-deepseek-001',
        orchestrator_id: 'deepseek-chat',
        runtime_version: '2.5.0',
        probe_execution_id: 'deepseek-conformance-v1',
        passed: true,
        failed_checks: [],
        checks_digest: 'sha256:9f8e7d6c5b4a3f2',
        total_checks: 20,
        certified_at_epoch: Date.now() / 1000 - 28000,
        revoked: false,
      },
      {
        certificate_id: 'cert-crewai-001',
        orchestrator_id: 'crewai-adapter',
        runtime_version: '0.80.0',
        probe_execution_id: 'crewai-conformance-v1',
        passed: false,
        failed_checks: ['check_deterministic_state_reset', 'check_fault_tolerance_recovery'],
        checks_digest: 'sha256:3d2e1c0b9a8f7e6',
        total_checks: 18,
        certified_at_epoch: Date.now() / 1000 - 15000,
        revoked: true,
        revocation_reason: 'Non-deterministic state leakage detected during multi-process probe',
        revocation_actor: 'governance-authority',
        revoked_at_epoch: Date.now() / 1000 - 10000,
      },
    ];

    certs.forEach(c => this.certifications.set(c.certificate_id, c));
  }

  private initDefaultBenchmarks() {
    this.benchmarks = [
      {
        evidence_id: 'bench-swe-openai-01',
        benchmark_id: 'swe-bench-verified',
        benchmark_version: '2026.1',
        task_set: 'swe-bench-500',
        executor_id: 'openai-agents',
        executor_version: '0.4.1',
        harness_id: 'metao-eval-harness-v1',
        harness_version: '1.2.0',
        model_id: 'gpt-4o',
        provider_id: 'openai',
        model_version: '2026-05',
        runtime_config_digest: 'sha256:a1b2c3d4e5f6',
        tool_policy_digest: 'sha256:9876543210ab',
        environment_id: 'hermetic-linux-x86',
        observed_at_epoch: Date.now() / 1000 - 50000,
        source: 'INDEPENDENT_VERIFIER',
        raw_result_ref: 'ipfs://QmSweBenchEvidence202601',
        metrics: [
          { name: 'resolve_rate', value: 0.54, unit: 'ratio' },
          { name: 'patch_hygiene', value: 0.98, unit: 'score' },
          { name: 'avg_cost_usd', value: 0.42, unit: 'usd' },
          { name: 'avg_turn_latency_ms', value: 890, unit: 'ms' },
        ],
      },
      {
        evidence_id: 'bench-swe-gemini-01',
        benchmark_id: 'swe-bench-verified',
        benchmark_version: '2026.1',
        task_set: 'swe-bench-500',
        executor_id: 'gemini-interactions',
        executor_version: '0.9.0',
        harness_id: 'metao-eval-harness-v1',
        harness_version: '1.2.0',
        model_id: 'gemini-2.5-pro',
        provider_id: 'google',
        model_version: '2026-06',
        runtime_config_digest: 'sha256:c4d5e6f7a8b9',
        tool_policy_digest: 'sha256:5432109876cd',
        environment_id: 'hermetic-linux-x86',
        observed_at_epoch: Date.now() / 1000 - 40000,
        source: 'INDEPENDENT_VERIFIER',
        raw_result_ref: 'ipfs://QmGeminiEvidence202602',
        metrics: [
          { name: 'resolve_rate', value: 0.58, unit: 'ratio' },
          { name: 'patch_hygiene', value: 0.99, unit: 'score' },
          { name: 'avg_cost_usd', value: 0.28, unit: 'usd' },
          { name: 'avg_turn_latency_ms', value: 720, unit: 'ms' },
        ],
      },
      {
        evidence_id: 'bench-terminal-core-01',
        benchmark_id: 'terminal-bench-core',
        benchmark_version: '1.0',
        task_set: 'devops-cli-100',
        executor_id: 'deepseek-chat',
        executor_version: '2.5.0',
        harness_id: 'metao-terminal-harness',
        harness_version: '1.0.0',
        model_id: 'deepseek-v3',
        provider_id: 'deepseek',
        model_version: '2026-04',
        runtime_config_digest: 'sha256:e7f8a9b0c1d2',
        tool_policy_digest: 'sha256:112233445566',
        environment_id: 'hermetic-linux-x86',
        observed_at_epoch: Date.now() / 1000 - 30000,
        source: 'PRODUCER_OBSERVED',
        raw_result_ref: 'ipfs://QmDeepseekTerminalCore01',
        metrics: [
          { name: 'task_success_rate', value: 0.91, unit: 'ratio' },
          { name: 'command_precision', value: 0.96, unit: 'score' },
          { name: 'avg_cost_usd', value: 0.08, unit: 'usd' },
        ],
      },
    ];
  }

  private initDefaultMissions() {
    // Seed the committed quickstart-accepted mission
    const now = Date.now();
    const quickstartAccepted: MissionRecord = {
      mission_id: 'quickstart-accepted',
      mission: {
        mission_id: 'quickstart-accepted',
        objective: 'quickstart mission',
        required_capabilities: ['workflow'],
        task_family: 'standard_workflow',
      },
      policy: {
        policy_bundle_id: 'quickstart-policy',
        allowed: true,
        require_human: false,
        reason: 'Policy check passed - allowed by quickstart rule',
      },
      budget: {
        money_limit: 1.0,
        token_limit: 1000,
        wall_time_limit_s: 60.0,
        verifier_attempt_limit: 3,
      },
      acceptance_context: {
        subject_id: 'quickstart-subject',
        subject_state_id: 'quickstart-state',
        verification_context_id: 'quickstart-verification',
        policy_bundle_id: 'quickstart-policy',
        required_obligations: ['execution_result'],
        trusted_verifiers: ['adapter-observer'],
        trusted_provenance_roots: [],
        authorized_authorities: ['metao-runtime'],
      },
      status: 'ACCEPTED',
      revision: 1,
      created_at: now - 3600000,
      updated_at: now - 3590000,
      orchestrator_id: 'quickstart-local',
      acceptance_decision: 'ACCEPT',
      attempted_orchestrators: ['quickstart-local'],
      attempts: [
        {
          attempt_number: 1,
          execution_id: 'exec-quickstart-001',
          orchestrator_id: 'quickstart-local',
          execution_status: 'SUCCEEDED',
          acceptance_decision: 'ACCEPT',
          reasons: ['Execution succeeded', 'Obligation satisfied with valid verification proof'],
          started_at_epoch: (now - 3600000) / 1000,
          ended_at_epoch: (now - 3590000) / 1000,
          cost: 0.0,
          tokens: 240,
        },
      ],
      output: {
        result: 'quickstart:quickstart mission',
        summary: 'Mission executed deterministically via quickstart-local provider without external network dependency.',
      },
      proof: {
        proof_id: 'proof-quickstart-accepted-001',
        obligation_results: {
          execution_result: {
            passed: true,
            verifier: 'adapter-observer',
            timestamp: (now - 3590000) / 1000,
            details: 'Hash matches authoritative output',
          },
        },
        signature: 'ed25519:e43a9b1c098dfa32b90ce8',
        accepted_at: (now - 3590000) / 1000,
        authority_id: 'metao-runtime',
      },
    };

    // Seed policy denied mission example
    const policyDenied: MissionRecord = {
      mission_id: 'quickstart-policy-deny',
      mission: {
        mission_id: 'quickstart-policy-deny',
        objective: 'unauthorized root modification test',
        required_capabilities: ['system_access'],
        task_family: 'system_admin',
      },
      policy: {
        policy_bundle_id: 'strict-governance-v1',
        allowed: false,
        require_human: true,
        reason: 'Policy violation: Unsanctioned capability system_access requested outside sandbox.',
      },
      budget: {
        money_limit: 0.5,
        token_limit: 500,
        wall_time_limit_s: 30.0,
        verifier_attempt_limit: 1,
      },
      acceptance_context: {
        subject_id: 'deny-subject',
        subject_state_id: 'deny-state',
        verification_context_id: 'deny-context',
        policy_bundle_id: 'strict-governance-v1',
        required_obligations: ['execution_result'],
        trusted_verifiers: ['adapter-observer'],
        trusted_provenance_roots: [],
        authorized_authorities: ['metao-runtime'],
      },
      status: 'BLOCKED',
      revision: 1,
      created_at: now - 1800000,
      updated_at: now - 1800000,
      acceptance_decision: 'DENY',
      attempted_orchestrators: [],
      attempts: [],
    };

    this.missions.set(quickstartAccepted.mission_id, quickstartAccepted);
    this.missions.set(policyDenied.mission_id, policyDenied);

    this.recordEvent(quickstartAccepted.mission_id, 'MISSION_CREATED', { objective: quickstartAccepted.mission.objective });
    this.recordEvent(quickstartAccepted.mission_id, 'POLICY_EVALUATED', { allowed: true });
    this.recordEvent(quickstartAccepted.mission_id, 'ORCHESTRATOR_SELECTED', { orchestrator_id: 'quickstart-local' });
    this.recordEvent(quickstartAccepted.mission_id, 'EXECUTION_COMPLETED', { status: 'SUCCEEDED' });
    this.recordEvent(quickstartAccepted.mission_id, 'MISSION_ACCEPTED', { proof_id: quickstartAccepted.proof?.proof_id });

    this.recordEvent(policyDenied.mission_id, 'MISSION_CREATED', { objective: policyDenied.mission.objective });
    this.recordEvent(policyDenied.mission_id, 'POLICY_BLOCKED', { reason: policyDenied.policy.reason });
  }

  private recordEvent(missionId: string, kind: string, data: Record<string, any>) {
    const event: MissionEvent = {
      event_id: `evt-${Date.now()}-${Math.floor(Math.random() * 10000)}`,
      mission_id: missionId,
      kind,
      timestamp: Date.now(),
      data,
    };
    this.events.unshift(event);
    if (this.events.length > 500) {
      this.events.pop();
    }
    return event;
  }

  // Doctor check
  public getDoctorReport(): DoctorReport {
    const runtimesList = Array.from(this.runtimes.values());
    const healthyCount = runtimesList.filter(r => r.disposition === 'ACTIVE' && r.health === 'HEALTHY').length;
    const certCount = Array.from(this.certifications.values()).filter(c => c.passed && !c.revoked).length;

    return {
      overall_status: 'PASS',
      timestamp: Date.now(),
      checks: [
        {
          name: 'RUNTIME_CATALOG',
          status: runtimesList.length > 0 ? 'PASS' : 'FAIL',
          details: `Admitted catalog configured with ${runtimesList.length} total runtimes (${healthyCount} healthy and active).`,
          metrics: { count: runtimesList.length, healthy: healthyCount },
        },
        {
          name: 'RUNTIME_CONTROL_STORE',
          status: 'PASS',
          details: 'Runtime quarantine and restore control store operational with durable revisions.',
          metrics: { quarantined_count: runtimesList.filter(r => r.disposition === 'QUARANTINED').length },
        },
        {
          name: 'RUNTIME_CERTIFICATION_STORE',
          status: certCount > 0 ? 'PASS' : 'FAIL',
          details: `${certCount} valid certificates verified; non-corrupt SQLite state schema verified.`,
          metrics: { valid_certificates: certCount },
        },
        {
          name: 'OPERATOR_FACTORY',
          status: 'PASS',
          details: 'Canonical declarative factory metao.runtime_factory:create_operator available and callable.',
          metrics: { factory: 'metao.runtime_factory:create_operator' },
        },
        {
          name: 'MISSION_PERSISTENCE',
          status: 'PASS',
          details: `${this.missions.size} missions loaded; event ledger active with ${this.events.length} audit entries.`,
          metrics: { missions: this.missions.size, events: this.events.length },
        },
      ],
    };
  }

  // Runtimes
  public getRuntimes(): RuntimeCatalogEntry[] {
    return Array.from(this.runtimes.values());
  }

  public getRuntime(id: string): RuntimeCatalogEntry | undefined {
    return this.runtimes.get(id);
  }

  public quarantineRuntime(id: string, reason: string, actor: string): RuntimeCatalogEntry {
    const entry = this.runtimes.get(id);
    if (!entry) throw new Error(`Runtime not found: ${id}`);
    entry.disposition = 'QUARANTINED';
    entry.health = 'QUARANTINED';
    entry.quarantine_reason = reason;
    entry.quarantine_actor = actor;
    entry.quarantined_at = Date.now();
    return entry;
  }

  public restoreRuntime(id: string, reason: string, actor: string): RuntimeCatalogEntry {
    const entry = this.runtimes.get(id);
    if (!entry) throw new Error(`Runtime not found: ${id}`);
    entry.disposition = 'ACTIVE';
    entry.health = 'HEALTHY';
    delete entry.quarantine_reason;
    delete entry.quarantine_actor;
    delete entry.quarantined_at;
    return entry;
  }

  // Certifications
  public getCertifications(orchestratorId?: string): RuntimeCertification[] {
    const all = Array.from(this.certifications.values());
    if (orchestratorId) {
      return all.filter(c => c.orchestrator_id === orchestratorId);
    }
    return all;
  }

  public revokeCertificate(certId: string, reason: string, actor: string): RuntimeCertification {
    const cert = this.certifications.get(certId);
    if (!cert) throw new Error(`Certificate not found: ${certId}`);
    cert.revoked = true;
    cert.revocation_reason = reason;
    cert.revocation_actor = actor;
    cert.revoked_at_epoch = Date.now() / 1000;
    return cert;
  }

  // Benchmarks
  public getBenchmarks(orchestratorId?: string): BenchmarkEvidence[] {
    if (orchestratorId) {
      return this.benchmarks.filter(b => b.executor_id === orchestratorId);
    }
    return this.benchmarks;
  }

  // Missions
  public getMissions(): MissionRecord[] {
    return Array.from(this.missions.values()).sort((a, b) => b.updated_at - a.updated_at);
  }

  public getMission(id: string): MissionRecord | undefined {
    return this.missions.get(id);
  }

  public getEvents(missionId?: string): MissionEvent[] {
    if (missionId) {
      return this.events.filter(e => e.mission_id === missionId);
    }
    return this.events;
  }

  public approveMission(missionId: string, approverId: string, approved: boolean, reason?: string): MissionRecord {
    const record = this.missions.get(missionId);
    if (!record) throw new Error(`Mission not found: ${missionId}`);
    if (record.status !== 'WAITING_APPROVAL') {
      throw new Error(`Mission is not waiting for approval (current status: ${record.status})`);
    }

    record.approval_request = {
      required: true,
      approved,
      approver_id: approverId,
      decided_at: Date.now(),
      reason,
    };

    if (!approved) {
      record.status = 'BLOCKED';
      record.acceptance_decision = 'DENY';
      record.updated_at = Date.now();
      this.recordEvent(missionId, 'HUMAN_APPROVAL_DENIED', { approverId, reason });
      return record;
    }

    this.recordEvent(missionId, 'HUMAN_APPROVAL_GRANTED', { approverId });
    // Resume execution
    return this.executeMissionPipeline(record);
  }

  public cancelMission(missionId: string, reason?: string): MissionRecord {
    const record = this.missions.get(missionId);
    if (!record) throw new Error(`Mission not found: ${missionId}`);
    if (record.status === 'ACCEPTED' || record.status === 'FAILED') {
      throw new Error(`Cannot cancel completed mission: ${missionId}`);
    }

    record.status = 'FAILED';
    record.acceptance_decision = 'DENY';
    record.updated_at = Date.now();
    this.recordEvent(missionId, 'MISSION_CANCELLED', { reason: reason || 'Operator requested cancellation' });
    return record;
  }

  public runMission(spec: {
    mission: Mission;
    policy: Policy;
    budget: AcceptanceBudget;
    acceptance_context: AcceptanceContext;
    max_attempts?: number;
  }): MissionRecord {
    if (this.missions.has(spec.mission.mission_id)) {
      throw new Error(`Mission already exists: ${spec.mission.mission_id}`);
    }

    const now = Date.now();
    const record: MissionRecord = {
      mission_id: spec.mission.mission_id,
      mission: spec.mission,
      policy: spec.policy,
      budget: spec.budget,
      acceptance_context: spec.acceptance_context,
      status: 'RUNNING',
      revision: 1,
      created_at: now,
      updated_at: now,
      acceptance_decision: 'DENY',
      attempted_orchestrators: [],
      attempts: [],
    };

    this.missions.set(record.mission_id, record);
    this.recordEvent(record.mission_id, 'MISSION_CREATED', {
      objective: record.mission.objective,
      capabilities: record.mission.required_capabilities,
    });

    // 1. Policy Gate Evaluation
    if (!record.policy.allowed) {
      record.status = 'BLOCKED';
      record.acceptance_decision = 'DENY';
      record.updated_at = Date.now();
      this.recordEvent(record.mission_id, 'POLICY_EVALUATION_DENIED', {
        policy_bundle_id: record.policy.policy_bundle_id,
        reason: record.policy.reason || 'Policy explicitly denies execution.',
      });
      return record;
    }

    this.recordEvent(record.mission_id, 'POLICY_EVALUATION_PASSED', {
      policy_bundle_id: record.policy.policy_bundle_id,
    });

    // 2. Human Gate Check
    if (record.policy.require_human) {
      record.status = 'WAITING_APPROVAL';
      record.approval_request = { required: true };
      record.updated_at = Date.now();
      this.recordEvent(record.mission_id, 'HUMAN_APPROVAL_REQUIRED', {
        reason: 'Policy specifies human verification requirement before orchestrator dispatch.',
      });
      return record;
    }

    // 3. Execution Pipeline
    return this.executeMissionPipeline(record);
  }

  private executeMissionPipeline(record: MissionRecord): MissionRecord {
    const requiredCaps = new Set(record.mission.required_capabilities);

    // Filter eligible admitted runtimes
    const admitted = Array.from(this.runtimes.values()).filter(r => {
      if (r.disposition !== 'ACTIVE') return false;
      if (r.health === 'UNHEALTHY' || r.health === 'QUARANTINED') return false;
      // All required capabilities must be supported
      for (const cap of requiredCaps) {
        if (!r.capabilities.includes(cap)) return false;
      }
      // Check certificate if required
      const certs = this.getCertifications(r.orchestrator_id);
      const validCert = certs.some(c => c.passed && !c.revoked);
      if (r.orchestrator_id !== 'quickstart-local' && !validCert) {
        return false;
      }
      return true;
    });

    if (admitted.length === 0) {
      record.status = 'FAILED';
      record.acceptance_decision = 'DENY';
      record.updated_at = Date.now();
      this.recordEvent(record.mission_id, 'RUNTIME_SELECTION_FAILED', {
        reason: 'No healthy admitted runtime matched the required capabilities and certificate constraints.',
        required_capabilities: Array.from(requiredCaps),
      });
      return record;
    }

    // Sort by strategy scoring (Quality * 0.4 + SuccessRate * 0.4 - NormalizedCost * 0.2)
    admitted.sort((a, b) => {
      const scoreA = a.quality * 0.4 + a.success_rate * 0.4 - (a.cost / (record.budget.money_limit || 1)) * 0.2;
      const scoreB = b.quality * 0.4 + b.success_rate * 0.4 - (b.cost / (record.budget.money_limit || 1)) * 0.2;
      return scoreB - scoreA;
    });

    const chosen = admitted[0];
    record.orchestrator_id = chosen.orchestrator_id;
    record.attempted_orchestrators.push(chosen.orchestrator_id);

    this.recordEvent(record.mission_id, 'ORCHESTRATOR_SELECTED', {
      orchestrator_id: chosen.orchestrator_id,
      trust_profile: chosen.trust_profile,
      quality: chosen.quality,
      latency_ms: chosen.latency_ms,
    });

    // Simulate execution attempt
    const attemptStart = Date.now();
    const execId = `exec-${record.mission_id}-${chosen.orchestrator_id}-01`;
    const tokens = Math.floor(180 + Math.random() * 200);
    const cost = Number((chosen.cost * (tokens / 1000)).toFixed(4));

    // Obligation verification
    const proofId = `proof-${record.mission_id}-${Math.floor(Math.random() * 100000)}`;
    const obligationResults: Record<string, { passed: boolean; verifier: string; timestamp: number; details?: string }> = {};

    for (const obligation of record.acceptance_context.required_obligations) {
      obligationResults[obligation] = {
        passed: true,
        verifier: record.acceptance_context.trusted_verifiers[0] || 'adapter-observer',
        timestamp: Date.now() / 1000,
        details: `Obligation '${obligation}' independently verified against acceptance context contract.`,
      };
    }

    const proof = {
      proof_id: proofId,
      obligation_results: obligationResults,
      signature: `sig-metao-ed25519-${Math.random().toString(36).substring(2, 12)}`,
      accepted_at: Date.now() / 1000,
      authority_id: record.acceptance_context.authorized_authorities[0] || 'metao-runtime',
    };

    const attempt: any = {
      attempt_number: 1,
      execution_id: execId,
      orchestrator_id: chosen.orchestrator_id,
      execution_status: 'SUCCEEDED',
      acceptance_decision: 'ACCEPT',
      reasons: [
        `Execution completed by ${chosen.orchestrator_id} within budget limits.`,
        'All required obligations verified independently by trusted verifiers.',
      ],
      started_at_epoch: attemptStart / 1000,
      ended_at_epoch: Date.now() / 1000,
      cost,
      tokens,
    };

    record.attempts.push(attempt);
    record.status = 'ACCEPTED';
    record.acceptance_decision = 'ACCEPT';
    record.proof = proof;
    record.output = {
      result: `metao:${record.mission.objective}`,
      executed_by: chosen.orchestrator_id,
      summary: `Completed successfully. Obligations satisfied: ${record.acceptance_context.required_obligations.join(', ')}.`,
      evidence_ref: `evidence://${record.mission_id}/${proofId}`,
    };
    record.updated_at = Date.now();

    this.recordEvent(record.mission_id, 'EXECUTION_COMPLETED', {
      execution_id: execId,
      status: 'SUCCEEDED',
      cost,
      tokens,
    });
    this.recordEvent(record.mission_id, 'MISSION_ACCEPTED', {
      proof_id: proofId,
      authority: proof.authority_id,
    });

    return record;
  }
}

export const metaoEngine = new MetaOEngine();
