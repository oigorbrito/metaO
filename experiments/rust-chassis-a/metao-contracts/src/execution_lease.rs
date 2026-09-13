use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionLeaseError {
    BlankIdentity(&'static str), BlankEvidenceRef, InvalidEvidenceBasis, ZeroGeneration, ZeroFencingToken,
    InvalidTimeWindow, LeaseBindingMismatch, GenerationRegression, FenceRegression, TimeRegression,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum LeaseState { Active, Released, Expired }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum LeaseAssurance { AuthoritativeStore, SingleInstanceDevelopment }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum LeaseEvidenceBasis { AuthoritativeStoreRead, DevelopmentLocal, CallerDeclared, Unknown }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionLease { pub mission_id:String,pub logical_execution_key:String,pub execution_id:String,pub holder_identity:String,pub generation:u64,pub fencing_token:u64,pub acquired_at_epoch:i64,pub renewed_at_epoch:i64,pub expires_at_epoch:i64,pub state:LeaseState,pub assurance:LeaseAssurance,pub evidence_basis:LeaseEvidenceBasis,pub evidence_ref:Option<String> }
impl ExecutionLease {
    pub fn validate(&self)->Result<(),ExecutionLeaseError>{for(name,value)in[("mission_id",self.mission_id.as_str()),("logical_execution_key",self.logical_execution_key.as_str()),("execution_id",self.execution_id.as_str()),("holder_identity",self.holder_identity.as_str())]{if value.trim().is_empty(){return Err(ExecutionLeaseError::BlankIdentity(name))}}match(self.assurance,self.evidence_basis){(LeaseAssurance::AuthoritativeStore,LeaseEvidenceBasis::AuthoritativeStoreRead)=>{if self.evidence_ref.as_deref().is_none_or(|v|v.trim().is_empty()){return Err(ExecutionLeaseError::BlankEvidenceRef)}},(LeaseAssurance::SingleInstanceDevelopment,LeaseEvidenceBasis::DevelopmentLocal)=>{},_=>return Err(ExecutionLeaseError::InvalidEvidenceBasis)}if self.generation==0{return Err(ExecutionLeaseError::ZeroGeneration)}if self.fencing_token==0{return Err(ExecutionLeaseError::ZeroFencingToken)}if self.renewed_at_epoch<self.acquired_at_epoch||self.expires_at_epoch<=self.renewed_at_epoch{return Err(ExecutionLeaseError::InvalidTimeWindow)}Ok(())}
    pub fn is_active_at(&self,now_epoch:i64)->bool{self.validate().is_ok()&&self.state==LeaseState::Active&&now_epoch>=self.renewed_at_epoch&&now_epoch<self.expires_at_epoch}
    pub fn authorizes(&self,presented_holder:&str,presented_generation:u64,presented_fence:u64,now_epoch:i64)->bool{self.is_active_at(now_epoch)&&self.holder_identity==presented_holder&&self.generation==presented_generation&&self.fencing_token==presented_fence}
    pub fn validate_successor(&self,successor:&ExecutionLease)->Result<(),ExecutionLeaseError>{self.validate()?;successor.validate()?;if successor.mission_id!=self.mission_id||successor.logical_execution_key!=self.logical_execution_key{return Err(ExecutionLeaseError::LeaseBindingMismatch)}if successor.generation<self.generation{return Err(ExecutionLeaseError::GenerationRegression)}if successor.fencing_token<self.fencing_token{return Err(ExecutionLeaseError::FenceRegression)}let changed=successor.holder_identity!=self.holder_identity||successor.execution_id!=self.execution_id||(self.state!=LeaseState::Active&&successor.state==LeaseState::Active);if changed&&successor.generation<=self.generation{return Err(ExecutionLeaseError::GenerationRegression)}if changed&&successor.fencing_token<=self.fencing_token{return Err(ExecutionLeaseError::FenceRegression)}if !changed&&(successor.renewed_at_epoch<self.renewed_at_epoch||successor.expires_at_epoch<self.expires_at_epoch){return Err(ExecutionLeaseError::TimeRegression)}Ok(())}
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum ExecutionRuntimeBindingBasis { CanonicalDispatch, AdapterVerified, CallerDeclared, Unknown }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRuntimeBindingProducer { pub producer_id:String,pub mission_id:String,pub logical_execution_key:String,pub execution_id:String,pub runtime_id:String,pub runtime_version:String,pub config_id:String,pub lease_generation:u64,pub fencing_token:u64,pub basis:ExecutionRuntimeBindingBasis,pub evidence_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionRuntimeBindingClaim { pub mission_id:String,pub logical_execution_key:String,pub execution_id:String,pub runtime_id:String,pub runtime_version:String,pub config_id:String,pub lease_generation:u64,pub fencing_token:u64 }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundExecutionRuntimeIdentity { pub producer_id:String,pub mission_id:String,pub logical_execution_key:String,pub execution_id:String,pub runtime_id:String,pub runtime_version:String,pub config_id:String,pub lease_generation:u64,pub fencing_token:u64,pub evidence_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum ExecutionRuntimeBindingError { InvalidProducer, LeaseBindingMismatch, ClaimBindingMismatch, StaleGenerationOrFence }
pub fn bind_execution_runtime_identity(claim:&ExecutionRuntimeBindingClaim,producer:&ExecutionRuntimeBindingProducer,current_lease:&ExecutionLease)->Result<BoundExecutionRuntimeIdentity,ExecutionRuntimeBindingError>{for value in[producer.producer_id.as_str(),producer.mission_id.as_str(),producer.logical_execution_key.as_str(),producer.execution_id.as_str(),producer.runtime_id.as_str(),producer.runtime_version.as_str(),producer.config_id.as_str(),producer.evidence_ref.as_str()]{if value.trim().is_empty(){return Err(ExecutionRuntimeBindingError::InvalidProducer)}}if producer.basis!=ExecutionRuntimeBindingBasis::CanonicalDispatch||producer.lease_generation==0||producer.fencing_token==0{return Err(ExecutionRuntimeBindingError::InvalidProducer)}current_lease.validate().map_err(|_|ExecutionRuntimeBindingError::LeaseBindingMismatch)?;if producer.mission_id!=current_lease.mission_id||producer.logical_execution_key!=current_lease.logical_execution_key||producer.execution_id!=current_lease.execution_id{return Err(ExecutionRuntimeBindingError::LeaseBindingMismatch)}if producer.lease_generation!=current_lease.generation||producer.fencing_token!=current_lease.fencing_token{return Err(ExecutionRuntimeBindingError::StaleGenerationOrFence)}if claim.mission_id!=producer.mission_id||claim.logical_execution_key!=producer.logical_execution_key||claim.execution_id!=producer.execution_id||claim.runtime_id!=producer.runtime_id||claim.runtime_version!=producer.runtime_version||claim.config_id!=producer.config_id||claim.lease_generation!=producer.lease_generation||claim.fencing_token!=producer.fencing_token{return Err(ExecutionRuntimeBindingError::ClaimBindingMismatch)}Ok(BoundExecutionRuntimeIdentity{producer_id:producer.producer_id.clone(),mission_id:producer.mission_id.clone(),logical_execution_key:producer.logical_execution_key.clone(),execution_id:producer.execution_id.clone(),runtime_id:producer.runtime_id.clone(),runtime_version:producer.runtime_version.clone(),config_id:producer.config_id.clone(),lease_generation:producer.lease_generation,fencing_token:producer.fencing_token,evidence_ref:producer.evidence_ref.clone()})}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExecutionResultLineageProducer { pub result_id:String,pub execution_id:String,pub runtime_id:String,pub runtime_version:String,pub config_id:String,pub lease_generation:u64,pub fencing_token:u64,pub health_observation_evidence_ref:String,pub result_evidence_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundRuntimeHealthObservationLineage { pub result_id:String,pub execution_id:String,pub runtime_id:String,pub runtime_version:String,pub config_id:String,pub lease_generation:u64,pub fencing_token:u64,pub observation_evidence_ref:String,pub result_evidence_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)] pub enum RuntimeHealthLineageError { InvalidResultProducer, RuntimeBindingMismatch, ObservationLineageMismatch }
pub fn bind_runtime_health_observation_lineage(identity:&BoundExecutionRuntimeIdentity,result:&ExecutionResultLineageProducer,observation:&crate::runtime_health::RuntimeHealthObservation)->Result<BoundRuntimeHealthObservationLineage,RuntimeHealthLineageError>{if result.result_id.trim().is_empty()||result.health_observation_evidence_ref.trim().is_empty()||result.result_evidence_ref.trim().is_empty(){return Err(RuntimeHealthLineageError::InvalidResultProducer)}if result.execution_id!=identity.execution_id||result.runtime_id!=identity.runtime_id||result.runtime_version!=identity.runtime_version||result.config_id!=identity.config_id||result.lease_generation!=identity.lease_generation||result.fencing_token!=identity.fencing_token{return Err(RuntimeHealthLineageError::RuntimeBindingMismatch)}if observation.runtime_id!=result.runtime_id||observation.runtime_version!=result.runtime_version||observation.config_id!=result.config_id||observation.evidence_ref!=result.health_observation_evidence_ref||observation.attempts==0{return Err(RuntimeHealthLineageError::ObservationLineageMismatch)}observation.validate().map_err(|_|RuntimeHealthLineageError::ObservationLineageMismatch)?;Ok(BoundRuntimeHealthObservationLineage{result_id:result.result_id.clone(),execution_id:result.execution_id.clone(),runtime_id:result.runtime_id.clone(),runtime_version:result.runtime_version.clone(),config_id:result.config_id.clone(),lease_generation:result.lease_generation,fencing_token:result.fencing_token,observation_evidence_ref:result.health_observation_evidence_ref.clone(),result_evidence_ref:result.result_evidence_ref.clone()})}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum AdmissionTimeBasis { TrustedControlPlaneClock, CallerDeclared, EvidenceMetadata, Unknown }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeHealthAdmissionAuthority { pub holder_identity:String,pub admitted_at_epoch:i64,pub time_basis:AdmissionTimeBasis,pub authority_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuthorizedRuntimeHealthAdmission { pub result_id:String,pub execution_id:String,pub runtime_id:String,pub lease_generation:u64,pub fencing_token:u64,pub admitted_at_epoch:i64,pub authority_ref:String }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthAdmissionError { InvalidAdmissionAuthority, LineageLeaseMismatch, StaleLeaseOrFence }

pub fn authorize_runtime_health_admission(
    lineage:&BoundRuntimeHealthObservationLineage,
    lease:&ExecutionLease,
    authority:&RuntimeHealthAdmissionAuthority,
)->Result<AuthorizedRuntimeHealthAdmission,RuntimeHealthAdmissionError>{
    if authority.holder_identity.trim().is_empty()||authority.authority_ref.trim().is_empty()||authority.time_basis!=AdmissionTimeBasis::TrustedControlPlaneClock{return Err(RuntimeHealthAdmissionError::InvalidAdmissionAuthority)}
    if lineage.execution_id!=lease.execution_id||lineage.lease_generation!=lease.generation||lineage.fencing_token!=lease.fencing_token{return Err(RuntimeHealthAdmissionError::LineageLeaseMismatch)}
    if !lease.authorizes(&authority.holder_identity,lineage.lease_generation,lineage.fencing_token,authority.admitted_at_epoch){return Err(RuntimeHealthAdmissionError::StaleLeaseOrFence)}
    Ok(AuthorizedRuntimeHealthAdmission{result_id:lineage.result_id.clone(),execution_id:lineage.execution_id.clone(),runtime_id:lineage.runtime_id.clone(),lease_generation:lineage.lease_generation,fencing_token:lineage.fencing_token,admitted_at_epoch:authority.admitted_at_epoch,authority_ref:authority.authority_ref.clone()})
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AdmittedRuntimeHealthFact {
    pub result_id: String,
    pub execution_id: String,
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
    pub lease_generation: u64,
    pub fencing_token: u64,
    pub admitted_at_epoch: i64,
    pub admission_authority_ref: String,
    pub observation_evidence_ref: String,
    pub result_evidence_ref: String,
    pub failure_origin_producer_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthFactAdmissionError {
    RuntimeIdentityBinding(ExecutionRuntimeBindingError),
    ResultLineage(RuntimeHealthLineageError),
    TrustedAdmission(RuntimeHealthAdmissionError),
    FailureOriginRequired,
    FailureOriginBindingMismatch,
    ExternalFailureOrigin,
}

pub fn admit_runtime_health_fact(
    claim: &ExecutionRuntimeBindingClaim,
    producer: &ExecutionRuntimeBindingProducer,
    result: &ExecutionResultLineageProducer,
    observation: &crate::runtime_health::RuntimeHealthObservation,
    lease: &ExecutionLease,
    authority: &RuntimeHealthAdmissionAuthority,
    failure_origin: Option<&crate::failure_causality::BoundFailureOrigin>,
) -> Result<AdmittedRuntimeHealthFact, RuntimeHealthFactAdmissionError> {
    let identity = bind_execution_runtime_identity(claim, producer, lease)
        .map_err(RuntimeHealthFactAdmissionError::RuntimeIdentityBinding)?;
    let lineage = bind_runtime_health_observation_lineage(&identity, result, observation)
        .map_err(RuntimeHealthFactAdmissionError::ResultLineage)?;
    let admission = authorize_runtime_health_admission(&lineage, lease, authority)
        .map_err(RuntimeHealthFactAdmissionError::TrustedAdmission)?;

    let failure_origin_producer_id = if observation.failures > 0 || observation.timeouts > 0 {
        let origin = failure_origin.ok_or(RuntimeHealthFactAdmissionError::FailureOriginRequired)?;
        if origin.mission_id.as_str() != identity.mission_id
            || origin.execution_id.as_ref().map(crate::ExecutionId::as_str) != Some(identity.execution_id.as_str())
            || !matches!(
                origin.original_outcome,
                Some(
                    crate::failure_causality::FactualExecutionOutcome::Failed
                        | crate::failure_causality::FactualExecutionOutcome::Timeout
                )
            )
        {
            return Err(RuntimeHealthFactAdmissionError::FailureOriginBindingMismatch);
        }
        if origin.origin != crate::failure_causality::FailureOrigin::RuntimeLocal
            || origin.producer_kind != crate::failure_causality::FailureOriginProducerKind::RuntimeExecution
        {
            return Err(RuntimeHealthFactAdmissionError::ExternalFailureOrigin);
        }
        Some(origin.producer_id.clone())
    } else {
        None
    };

    Ok(AdmittedRuntimeHealthFact {
        result_id: lineage.result_id,
        execution_id: lineage.execution_id,
        runtime_id: lineage.runtime_id,
        runtime_version: lineage.runtime_version,
        config_id: lineage.config_id,
        lease_generation: admission.lease_generation,
        fencing_token: admission.fencing_token,
        admitted_at_epoch: admission.admitted_at_epoch,
        admission_authority_ref: admission.authority_ref,
        observation_evidence_ref: lineage.observation_evidence_ref,
        result_evidence_ref: lineage.result_evidence_ref,
        failure_origin_producer_id,
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthConstituentOutcome { Succeeded, RuntimeLocalFailed, RuntimeLocalTimeout }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct AdmittedRuntimeHealthConstituent {
    pub fact: AdmittedRuntimeHealthFact,
    pub sequence: u64,
    pub outcome: RuntimeHealthConstituentOutcome,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeHealthConstituentError {
    NotSingleExecutionObservation,
    InvalidSingleExecutionCounters,
    OriginOutcomeMismatch,
    Admission(RuntimeHealthFactAdmissionError),
    EmptyConstituentSet,
    RuntimeTupleMismatch,
    DuplicateResultConflict,
    SequenceConflict,
}

pub fn admit_runtime_health_constituent(
    claim: &ExecutionRuntimeBindingClaim,
    producer: &ExecutionRuntimeBindingProducer,
    result: &ExecutionResultLineageProducer,
    observation: &crate::runtime_health::RuntimeHealthObservation,
    lease: &ExecutionLease,
    authority: &RuntimeHealthAdmissionAuthority,
    failure_origin: Option<&crate::failure_causality::BoundFailureOrigin>,
) -> Result<AdmittedRuntimeHealthConstituent, RuntimeHealthConstituentError> {
    if observation.attempts != 1 || observation.window_start_sequence != observation.window_end_sequence {
        return Err(RuntimeHealthConstituentError::NotSingleExecutionObservation);
    }
    let outcome = match (observation.successes, observation.failures, observation.timeouts) {
        (1, 0, 0) => RuntimeHealthConstituentOutcome::Succeeded,
        (0, 1, 0) => RuntimeHealthConstituentOutcome::RuntimeLocalFailed,
        (0, 1, 1) => RuntimeHealthConstituentOutcome::RuntimeLocalTimeout,
        _ => return Err(RuntimeHealthConstituentError::InvalidSingleExecutionCounters),
    };
    if let Some(origin) = failure_origin {
        let outcome_matches = matches!(
            (outcome, origin.original_outcome),
            (RuntimeHealthConstituentOutcome::RuntimeLocalFailed, Some(crate::failure_causality::FactualExecutionOutcome::Failed))
                | (RuntimeHealthConstituentOutcome::RuntimeLocalTimeout, Some(crate::failure_causality::FactualExecutionOutcome::Timeout))
        );
        if outcome != RuntimeHealthConstituentOutcome::Succeeded && !outcome_matches {
            return Err(RuntimeHealthConstituentError::OriginOutcomeMismatch);
        }
    }
    let fact = admit_runtime_health_fact(claim, producer, result, observation, lease, authority, failure_origin)
        .map_err(RuntimeHealthConstituentError::Admission)?;
    Ok(AdmittedRuntimeHealthConstituent {
        fact,
        sequence: observation.window_start_sequence,
        outcome,
    })
}

pub fn aggregate_runtime_health_constituents(
    constituents: &[AdmittedRuntimeHealthConstituent],
    active_retries: u32,
    prior_state: Option<crate::runtime_health::RuntimeHealthState>,
    self_reported_healthy: Option<bool>,
) -> Result<crate::runtime_health::RuntimeHealthObservation, RuntimeHealthConstituentError> {
    use std::collections::BTreeMap;
    if constituents.is_empty() {
        return Err(RuntimeHealthConstituentError::EmptyConstituentSet);
    }
    let first = &constituents[0];
    let mut by_result: BTreeMap<&str, &AdmittedRuntimeHealthConstituent> = BTreeMap::new();
    let mut by_sequence: BTreeMap<u64, &str> = BTreeMap::new();
    for constituent in constituents {
        if constituent.fact.runtime_id != first.fact.runtime_id
            || constituent.fact.runtime_version != first.fact.runtime_version
            || constituent.fact.config_id != first.fact.config_id
        {
            return Err(RuntimeHealthConstituentError::RuntimeTupleMismatch);
        }
        if let Some(existing) = by_result.get(constituent.fact.result_id.as_str()) {
            if *existing != constituent {
                return Err(RuntimeHealthConstituentError::DuplicateResultConflict);
            }
            continue;
        }
        if let Some(existing_result) = by_sequence.get(&constituent.sequence) {
            if *existing_result != constituent.fact.result_id.as_str() {
                return Err(RuntimeHealthConstituentError::SequenceConflict);
            }
        }
        by_sequence.insert(constituent.sequence, constituent.fact.result_id.as_str());
        by_result.insert(constituent.fact.result_id.as_str(), constituent);
    }
    let mut ordered: Vec<&AdmittedRuntimeHealthConstituent> = by_result.values().copied().collect();
    ordered.sort_by_key(|item| item.sequence);
    let attempts = u32::try_from(ordered.len()).unwrap_or(u32::MAX);
    let successes = u32::try_from(ordered.iter().filter(|item| item.outcome == RuntimeHealthConstituentOutcome::Succeeded).count()).unwrap_or(u32::MAX);
    let failures = attempts.saturating_sub(successes);
    let timeouts = u32::try_from(ordered.iter().filter(|item| item.outcome == RuntimeHealthConstituentOutcome::RuntimeLocalTimeout).count()).unwrap_or(u32::MAX);
    let mut consecutive_failures = 0u32;
    for item in ordered.iter().rev() {
        if item.outcome == RuntimeHealthConstituentOutcome::Succeeded { break; }
        consecutive_failures = consecutive_failures.saturating_add(1);
    }
    let fresh_successes_since_unhealthy = if matches!(prior_state, Some(crate::runtime_health::RuntimeHealthState::Unhealthy | crate::runtime_health::RuntimeHealthState::Quarantined | crate::runtime_health::RuntimeHealthState::Recovering)) {
        u32::try_from(ordered.iter().rev().take_while(|item| item.outcome == RuntimeHealthConstituentOutcome::Succeeded).count()).unwrap_or(u32::MAX)
    } else { 0 };
    Ok(crate::runtime_health::RuntimeHealthObservation {
        runtime_id: first.fact.runtime_id.clone(),
        runtime_version: first.fact.runtime_version.clone(),
        config_id: first.fact.config_id.clone(),
        evidence_basis: crate::runtime_health::RuntimeHealthEvidenceBasis::IndependentObservation,
        evidence_ref: format!("admitted-runtime-health-window:{}:{}", first.fact.runtime_id, by_result.keys().copied().collect::<Vec<_>>().join(",")),
        window_start_sequence: ordered.first().map(|item| item.sequence).unwrap_or(0),
        window_end_sequence: ordered.last().map(|item| item.sequence).unwrap_or(0),
        attempts,
        successes,
        failures,
        consecutive_failures,
        timeouts,
        transport_failures: 0,
        active_retries,
        fresh_successes_since_unhealthy,
        prior_state,
        self_reported_healthy,
    })
}
