use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum EngineeringKnowledgeError {
    BlankSourceId,
    BlankLocator,
    BlankClaimId,
    BlankEvidenceRef,
    InvalidFreshnessPolicy,
    InvalidConfidence,
    InvalidOverride,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum SourceKind {
    ProjectDocumentation,
    ProviderDocumentation,
    EngineeringStandard,
    PeerReviewedResearch,
    EmpiricalTest,
    RepositoryObservation,
    RuntimeObservation,
    SecurityAdvisory,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum EvidenceStrength {
    Anecdotal,
    Documented,
    IndependentlyObserved,
    EmpiricallyReproduced,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FreshnessPolicy {
    pub max_age_s: u64,
    pub refresh_interval_s: u64,
}

impl FreshnessPolicy {
    pub fn validate(&self) -> Result<(), EngineeringKnowledgeError> {
        if self.max_age_s == 0 || self.refresh_interval_s == 0 {
            return Err(EngineeringKnowledgeError::InvalidFreshnessPolicy);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct KnowledgeSource {
    pub source_id: String,
    pub kind: SourceKind,
    pub locator: String,
    pub authorized: bool,
    pub observed_at_epoch_s: u64,
    pub freshness: FreshnessPolicy,
    pub vendor_or_country: Option<String>,
}

impl KnowledgeSource {
    pub fn validate(&self) -> Result<(), EngineeringKnowledgeError> {
        if self.source_id.trim().is_empty() {
            return Err(EngineeringKnowledgeError::BlankSourceId);
        }
        if self.locator.trim().is_empty() {
            return Err(EngineeringKnowledgeError::BlankLocator);
        }
        self.freshness.validate()
    }

    pub fn is_fresh(&self, now_epoch_s: u64) -> bool {
        now_epoch_s.saturating_sub(self.observed_at_epoch_s) <= self.freshness.max_age_s
    }

    pub fn refresh_due(&self, now_epoch_s: u64) -> bool {
        now_epoch_s.saturating_sub(self.observed_at_epoch_s) >= self.freshness.refresh_interval_s
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClaimDisposition {
    SupportsRequestedAction,
    ConflictsWithRequestedAction,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConstraintClass {
    Advisory,
    HardSafetyOrPolicy,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineeringClaim {
    pub claim_id: String,
    pub source_id: String,
    pub disposition: ClaimDisposition,
    pub constraint_class: ConstraintClass,
    pub strength: EvidenceStrength,
    pub confidence_basis_points: u16,
    pub evidence_ref: String,
}

impl EngineeringClaim {
    pub fn validate(&self) -> Result<(), EngineeringKnowledgeError> {
        if self.claim_id.trim().is_empty() {
            return Err(EngineeringKnowledgeError::BlankClaimId);
        }
        if self.evidence_ref.trim().is_empty() {
            return Err(EngineeringKnowledgeError::BlankEvidenceRef);
        }
        if self.confidence_basis_points > 10_000 {
            return Err(EngineeringKnowledgeError::InvalidConfidence);
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum DecisionRisk {
    Low,
    Material,
    High,
    Irreversible,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum EngineeringAuthorityAction {
    Proceed,
    Warn,
    RequireConfirmation,
    RequireRefresh,
    Block,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineeringDecision {
    pub action: EngineeringAuthorityAction,
    pub supporting_claim_ids: Vec<String>,
    pub conflicting_claim_ids: Vec<String>,
    pub stale_source_ids: Vec<String>,
    pub required_confirmations: u8,
    pub rationale: Vec<String>,
}

fn source_authority(kind: SourceKind) -> u8 {
    match kind {
        SourceKind::ProjectDocumentation => 1,
        SourceKind::ProviderDocumentation => 2,
        SourceKind::EngineeringStandard | SourceKind::PeerReviewedResearch => 3,
        SourceKind::SecurityAdvisory => 4,
        SourceKind::RepositoryObservation | SourceKind::RuntimeObservation => 4,
        SourceKind::EmpiricalTest => 5,
    }
}

fn confirmation_depth(risk: DecisionRisk) -> u8 {
    match risk {
        DecisionRisk::Low => 0,
        DecisionRisk::Material => 1,
        DecisionRisk::High => 2,
        DecisionRisk::Irreversible => 3,
    }
}

pub fn evaluate_engineering_authority(
    sources: &[KnowledgeSource],
    claims: &[EngineeringClaim],
    risk: DecisionRisk,
    now_epoch_s: u64,
) -> Result<EngineeringDecision, EngineeringKnowledgeError> {
    for source in sources {
        source.validate()?;
    }
    for claim in claims {
        claim.validate()?;
    }

    let mut supporting = Vec::new();
    let mut conflicting = Vec::new();
    let mut stale = Vec::new();
    let mut strongest_support = 0u16;
    let mut strongest_conflict = 0u16;
    let mut hard_conflict = false;
    let mut authoritative_claims = 0usize;

    for claim in claims {
        let Some(source) = sources
            .iter()
            .find(|source| source.source_id == claim.source_id)
        else {
            continue;
        };
        if !source.authorized {
            continue;
        }
        if !source.is_fresh(now_epoch_s) {
            if !stale.contains(&source.source_id) {
                stale.push(source.source_id.clone());
            }
            continue;
        }

        authoritative_claims += 1;
        let score = u16::from(source_authority(source.kind)) * 10_000
            + u16::from(claim.strength as u8) * 1_000
            + claim.confidence_basis_points / 10;

        match claim.disposition {
            ClaimDisposition::SupportsRequestedAction => {
                supporting.push(claim.claim_id.clone());
                strongest_support = strongest_support.max(score);
            }
            ClaimDisposition::ConflictsWithRequestedAction => {
                conflicting.push(claim.claim_id.clone());
                strongest_conflict = strongest_conflict.max(score);
                hard_conflict |=
                    matches!(claim.constraint_class, ConstraintClass::HardSafetyOrPolicy);
            }
        }
    }

    let mut rationale = Vec::new();
    let action = if hard_conflict {
        rationale.push(
            "fresh authorized evidence establishes a hard safety/policy conflict".to_string(),
        );
        EngineeringAuthorityAction::Block
    } else if authoritative_claims == 0 {
        if !stale.is_empty() {
            rationale.push(
                "material decision depends on stale evidence and requires refresh".to_string(),
            );
            EngineeringAuthorityAction::RequireRefresh
        } else if matches!(risk, DecisionRisk::Low) {
            rationale.push(
                "no authoritative evidence is available; low-risk action may proceed with warning"
                    .to_string(),
            );
            EngineeringAuthorityAction::Warn
        } else {
            rationale
                .push("no authoritative evidence is available for a material decision".to_string());
            EngineeringAuthorityAction::Block
        }
    } else if strongest_conflict > strongest_support {
        rationale.push(
            "stronger current engineering evidence conflicts with the requested action".to_string(),
        );
        if matches!(risk, DecisionRisk::Low) {
            EngineeringAuthorityAction::Warn
        } else {
            EngineeringAuthorityAction::RequireConfirmation
        }
    } else {
        rationale.push("current authorized evidence supports or does not materially oppose the requested action".to_string());
        EngineeringAuthorityAction::Proceed
    };

    Ok(EngineeringDecision {
        action,
        supporting_claim_ids: supporting,
        conflicting_claim_ids: conflicting,
        stale_source_ids: stale,
        required_confirmations: if matches!(action, EngineeringAuthorityAction::RequireConfirmation)
        {
            confirmation_depth(risk)
        } else {
            0
        },
        rationale,
    })
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct UserOverride {
    pub confirmation_count: u8,
    pub rationale: String,
    pub evidence_acknowledged: bool,
}

pub fn apply_user_override(
    decision: &EngineeringDecision,
    override_record: &UserOverride,
) -> Result<EngineeringDecision, EngineeringKnowledgeError> {
    if override_record.rationale.trim().is_empty() || !override_record.evidence_acknowledged {
        return Err(EngineeringKnowledgeError::InvalidOverride);
    }
    if matches!(
        decision.action,
        EngineeringAuthorityAction::Block | EngineeringAuthorityAction::RequireRefresh
    ) {
        return Err(EngineeringKnowledgeError::InvalidOverride);
    }
    if decision.action != EngineeringAuthorityAction::RequireConfirmation {
        return Ok(decision.clone());
    }
    if override_record.confirmation_count < decision.required_confirmations {
        return Err(EngineeringKnowledgeError::InvalidOverride);
    }

    let mut overridden = decision.clone();
    overridden.action = EngineeringAuthorityAction::Proceed;
    overridden.rationale.push(
        "user explicitly accepted a documented non-hard engineering deviation; adverse evidence remains authoritative history"
            .to_string(),
    );
    Ok(overridden)
}
