use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeSecurityError {
    BlankBindingField(&'static str),
    BlankEvidenceRef,
    BlankSetEntry(&'static str),
    EmptyProfile,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum IsolationAssurance {
    Unknown,
    None,
    Process,
    ContainerOrEquivalent,
    StrongerAttested,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeSecurityEvidenceBasis {
    IndependentObservation,
    AdapterVerified,
    SelfReported,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeSecurityBinding {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
}

impl RuntimeSecurityBinding {
    pub fn validate(&self) -> Result<(), RuntimeSecurityError> {
        for (name, value) in [
            ("runtime_id", self.runtime_id.as_str()),
            ("runtime_version", self.runtime_version.as_str()),
            ("config_id", self.config_id.as_str()),
        ] {
            if value.trim().is_empty() {
                return Err(RuntimeSecurityError::BlankBindingField(name));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeSecurityFacts {
    pub binding: RuntimeSecurityBinding,
    pub isolation: IsolationAssurance,
    pub effective_permissions: BTreeSet<String>,
    pub secret_redaction_enforced: Option<bool>,
    pub untrusted_content_isolated_from_governance: Option<bool>,
    pub enforcement_capabilities: BTreeSet<String>,
    pub evidence_basis: RuntimeSecurityEvidenceBasis,
    pub evidence_ref: String,
}

impl RuntimeSecurityFacts {
    pub fn validate(&self) -> Result<(), RuntimeSecurityError> {
        self.binding.validate()?;
        if self.evidence_ref.trim().is_empty() {
            return Err(RuntimeSecurityError::BlankEvidenceRef);
        }
        if self
            .effective_permissions
            .iter()
            .any(|permission| permission.trim().is_empty())
        {
            return Err(RuntimeSecurityError::BlankSetEntry(
                "effective_permissions",
            ));
        }
        if self
            .enforcement_capabilities
            .iter()
            .any(|capability| capability.trim().is_empty())
        {
            return Err(RuntimeSecurityError::BlankSetEntry(
                "enforcement_capabilities",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeSecurityProfile {
    pub minimum_isolation: IsolationAssurance,
    pub allowed_permissions: BTreeSet<String>,
    pub require_secret_redaction: bool,
    pub require_untrusted_content_isolation: bool,
    pub required_capabilities: BTreeSet<String>,
}

impl RuntimeSecurityProfile {
    pub fn validate(&self) -> Result<(), RuntimeSecurityError> {
        if self.minimum_isolation == IsolationAssurance::Unknown
            && self.allowed_permissions.is_empty()
            && !self.require_secret_redaction
            && !self.require_untrusted_content_isolation
            && self.required_capabilities.is_empty()
        {
            return Err(RuntimeSecurityError::EmptyProfile);
        }
        if self
            .allowed_permissions
            .iter()
            .any(|permission| permission.trim().is_empty())
        {
            return Err(RuntimeSecurityError::BlankSetEntry(
                "allowed_permissions",
            ));
        }
        if self
            .required_capabilities
            .iter()
            .any(|capability| capability.trim().is_empty())
        {
            return Err(RuntimeSecurityError::BlankSetEntry(
                "required_capabilities",
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum RuntimeSecurityAdmission {
    Satisfied,
    Rejected,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeSecurityProjection {
    pub binding: RuntimeSecurityBinding,
    pub admission: RuntimeSecurityAdmission,
    pub reasons: Vec<String>,
}

pub fn evaluate_runtime_security(
    facts: &RuntimeSecurityFacts,
    profile: &RuntimeSecurityProfile,
    expected_binding: &RuntimeSecurityBinding,
) -> Result<RuntimeSecurityProjection, RuntimeSecurityError> {
    facts.validate()?;
    profile.validate()?;
    expected_binding.validate()?;

    let mut reasons = Vec::new();

    if &facts.binding != expected_binding {
        reasons.push("runtime security evidence binding does not match current runtime/version/config".to_string());
    }

    if !matches!(
        facts.evidence_basis,
        RuntimeSecurityEvidenceBasis::IndependentObservation
            | RuntimeSecurityEvidenceBasis::AdapterVerified
    ) {
        reasons.push(
            "runtime security enforcement is not backed by independent or adapter-verified evidence"
                .to_string(),
        );
    }

    if facts.isolation == IsolationAssurance::Unknown
        || facts.isolation < profile.minimum_isolation
    {
        reasons.push(format!(
            "isolation assurance {:?} does not satisfy minimum {:?}",
            facts.isolation, profile.minimum_isolation
        ));
    }

    for permission in &facts.effective_permissions {
        if !profile.allowed_permissions.contains(permission) {
            reasons.push(format!("effective permission {permission} is outside authorized profile"));
        }
    }

    if profile.require_secret_redaction && facts.secret_redaction_enforced != Some(true) {
        reasons.push("required secret-redaction enforcement is not proven".to_string());
    }

    if profile.require_untrusted_content_isolation
        && facts.untrusted_content_isolated_from_governance != Some(true)
    {
        reasons.push("untrusted content is not proven isolated from governance authority".to_string());
    }

    for capability in &profile.required_capabilities {
        if !facts.enforcement_capabilities.contains(capability) {
            reasons.push(format!("required enforcement capability {capability} is missing"));
        }
    }

    Ok(RuntimeSecurityProjection {
        binding: facts.binding.clone(),
        admission: if reasons.is_empty() {
            RuntimeSecurityAdmission::Satisfied
        } else {
            RuntimeSecurityAdmission::Rejected
        },
        reasons,
    })
}
