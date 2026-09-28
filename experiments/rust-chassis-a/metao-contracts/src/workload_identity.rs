use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadIdentityError {
    BlankRuntimeId,
    BlankRuntimeVersion,
    BlankConfigId,
    BlankWorkloadSubject,
    BlankTrustDomain,
    BlankTrustRootRef,
    BlankCredentialRef,
    BlankVerifierProvenance,
    MissingIssuedAt,
    MissingExpiresAt,
    MissingVerifiedAt,
    InvalidAttestedCredential,
    InvalidAssuranceCredentialPair,
    InvalidVerificationBasis,
    InvalidValidityWindow,
    SpiffeTrustDomainMismatch,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadCredentialKind {
    X509Svid,
    JwtSvid,
    OtherAttested,
    Development,
    Unsupported,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadIdentityAssurance {
    Attested,
    Unverified,
    Development,
    Unsupported,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadIdentityEvidenceBasis {
    IdentityProviderVerified,
    IndependentVerifier,
    SelfReported,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadIdentityTrustConfigurationBasis {
    AuthoritativeConfiguration,
    CallerDeclared,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkloadIdentityTrustConfiguration {
    pub configuration_ref: String,
    pub trust_domain: String,
    pub trusted_root_refs: BTreeSet<String>,
    pub basis: WorkloadIdentityTrustConfigurationBasis,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkloadIdentityAdmissionError {
    InvalidIdentity(WorkloadIdentityError),
    BlankConfigurationRef,
    BlankTrustDomain,
    EmptyTrustedRootSet,
    BlankTrustedRootRef,
    NonAuthoritativeTrustConfiguration,
    IdentityNotAttested,
    IdentityNotCurrentlyApplicable,
    RuntimeBindingMismatch,
    TrustDomainMismatch,
    UntrustedTrustRoot,
    InvalidExecutionIdentity,
}

impl WorkloadIdentityTrustConfiguration {
    pub fn validate(&self) -> Result<(), WorkloadIdentityAdmissionError> {
        if self.configuration_ref.trim().is_empty() {
            return Err(WorkloadIdentityAdmissionError::BlankConfigurationRef);
        }
        if self.trust_domain.trim().is_empty() {
            return Err(WorkloadIdentityAdmissionError::BlankTrustDomain);
        }
        if self.trusted_root_refs.is_empty() {
            return Err(WorkloadIdentityAdmissionError::EmptyTrustedRootSet);
        }
        if self
            .trusted_root_refs
            .iter()
            .any(|value| value.trim().is_empty())
        {
            return Err(WorkloadIdentityAdmissionError::BlankTrustedRootRef);
        }
        if self.basis != WorkloadIdentityTrustConfigurationBasis::AuthoritativeConfiguration {
            return Err(WorkloadIdentityAdmissionError::NonAuthoritativeTrustConfiguration);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeIdentityBinding {
    pub runtime_id: String,
    pub runtime_version: String,
    pub config_id: String,
}

impl RuntimeIdentityBinding {
    pub fn validate(&self) -> Result<(), WorkloadIdentityError> {
        if self.runtime_id.trim().is_empty() {
            return Err(WorkloadIdentityError::BlankRuntimeId);
        }
        if self.runtime_version.trim().is_empty() {
            return Err(WorkloadIdentityError::BlankRuntimeVersion);
        }
        if self.config_id.trim().is_empty() {
            return Err(WorkloadIdentityError::BlankConfigId);
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeWorkloadIdentity {
    pub binding: RuntimeIdentityBinding,
    pub workload_subject: String,
    pub trust_domain: String,
    pub credential_kind: WorkloadCredentialKind,
    pub assurance: WorkloadIdentityAssurance,
    pub evidence_basis: WorkloadIdentityEvidenceBasis,
    pub trust_root_ref: Option<String>,
    pub credential_ref: Option<String>,
    pub verifier_provenance: Option<String>,
    pub issued_at_epoch: Option<i64>,
    pub expires_at_epoch: Option<i64>,
    pub verified_at_epoch: Option<i64>,
}

impl RuntimeWorkloadIdentity {
    pub fn new(value: Self) -> Result<Self, WorkloadIdentityError> {
        value.validate()?;
        Ok(value)
    }

    pub fn validate(&self) -> Result<(), WorkloadIdentityError> {
        self.binding.validate()?;

        if self.workload_subject.trim().is_empty() {
            return Err(WorkloadIdentityError::BlankWorkloadSubject);
        }
        if self.trust_domain.trim().is_empty() {
            return Err(WorkloadIdentityError::BlankTrustDomain);
        }

        if matches!(
            self.credential_kind,
            WorkloadCredentialKind::X509Svid | WorkloadCredentialKind::JwtSvid
        ) {
            let expected_prefix = format!("spiffe://{}/", self.trust_domain.trim());
            if !self.workload_subject.starts_with(&expected_prefix) {
                return Err(WorkloadIdentityError::SpiffeTrustDomainMismatch);
            }
        }

        if let (Some(issued), Some(expires)) = (self.issued_at_epoch, self.expires_at_epoch) {
            if expires <= issued {
                return Err(WorkloadIdentityError::InvalidValidityWindow);
            }
        }
        if let (Some(issued), Some(expires), Some(verified)) = (
            self.issued_at_epoch,
            self.expires_at_epoch,
            self.verified_at_epoch,
        ) {
            if verified < issued || verified >= expires {
                return Err(WorkloadIdentityError::InvalidValidityWindow);
            }
        }

        match self.assurance {
            WorkloadIdentityAssurance::Attested => {
                if matches!(
                    self.credential_kind,
                    WorkloadCredentialKind::Development | WorkloadCredentialKind::Unsupported
                ) {
                    return Err(WorkloadIdentityError::InvalidAttestedCredential);
                }
                if !matches!(
                    self.evidence_basis,
                    WorkloadIdentityEvidenceBasis::IdentityProviderVerified
                        | WorkloadIdentityEvidenceBasis::IndependentVerifier
                ) {
                    return Err(WorkloadIdentityError::InvalidVerificationBasis);
                }
                if self
                    .trust_root_ref
                    .as_deref()
                    .is_none_or(|value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankTrustRootRef);
                }
                if self
                    .credential_ref
                    .as_deref()
                    .is_none_or(|value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankCredentialRef);
                }
                if self
                    .verifier_provenance
                    .as_deref()
                    .is_none_or(|value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankVerifierProvenance);
                }
                if self.issued_at_epoch.is_none() {
                    return Err(WorkloadIdentityError::MissingIssuedAt);
                }
                if self.expires_at_epoch.is_none() {
                    return Err(WorkloadIdentityError::MissingExpiresAt);
                }
                if self.verified_at_epoch.is_none() {
                    return Err(WorkloadIdentityError::MissingVerifiedAt);
                }
            }
            WorkloadIdentityAssurance::Development => {
                if self.credential_kind != WorkloadCredentialKind::Development {
                    return Err(WorkloadIdentityError::InvalidAssuranceCredentialPair);
                }
            }
            WorkloadIdentityAssurance::Unsupported => {
                if self.credential_kind != WorkloadCredentialKind::Unsupported {
                    return Err(WorkloadIdentityError::InvalidAssuranceCredentialPair);
                }
            }
            WorkloadIdentityAssurance::Unverified => {}
        }

        Ok(())
    }

    pub fn is_currently_applicable(&self, now_epoch: i64) -> bool {
        if self.validate().is_err() || self.assurance != WorkloadIdentityAssurance::Attested {
            return false;
        }
        let Some(issued) = self.issued_at_epoch else {
            return false;
        };
        let Some(expires) = self.expires_at_epoch else {
            return false;
        };
        now_epoch >= issued && now_epoch < expires
    }

    pub fn applies_to(&self, runtime_id: &str, runtime_version: &str, config_id: &str) -> bool {
        self.validate().is_ok()
            && self.binding.runtime_id == runtime_id
            && self.binding.runtime_version == runtime_version
            && self.binding.config_id == config_id
    }

    pub fn validate_against_trust_configuration(
        &self,
        expected_binding: &RuntimeIdentityBinding,
        trust_configuration: &WorkloadIdentityTrustConfiguration,
        now_epoch: i64,
    ) -> Result<(), WorkloadIdentityAdmissionError> {
        trust_configuration.validate()?;
        expected_binding
            .validate()
            .map_err(WorkloadIdentityAdmissionError::InvalidIdentity)?;
        self.validate()
            .map_err(WorkloadIdentityAdmissionError::InvalidIdentity)?;

        if self.assurance != WorkloadIdentityAssurance::Attested {
            return Err(WorkloadIdentityAdmissionError::IdentityNotAttested);
        }
        if !self.is_currently_applicable(now_epoch) {
            return Err(WorkloadIdentityAdmissionError::IdentityNotCurrentlyApplicable);
        }
        if &self.binding != expected_binding {
            return Err(WorkloadIdentityAdmissionError::RuntimeBindingMismatch);
        }
        if self.trust_domain != trust_configuration.trust_domain {
            return Err(WorkloadIdentityAdmissionError::TrustDomainMismatch);
        }

        let trust_root_ref = self
            .trust_root_ref
            .as_deref()
            .ok_or(WorkloadIdentityAdmissionError::UntrustedTrustRoot)?;
        if !trust_configuration.trusted_root_refs.contains(trust_root_ref) {
            return Err(WorkloadIdentityAdmissionError::UntrustedTrustRoot);
        }
        Ok(())
    }

    pub fn validate_for_execution_runtime(
        &self,
        execution_identity: &crate::execution_lease::BoundExecutionRuntimeIdentity,
        trust_configuration: &WorkloadIdentityTrustConfiguration,
        now_epoch: i64,
    ) -> Result<(), WorkloadIdentityAdmissionError> {
        for value in [
            execution_identity.producer_id.as_str(),
            execution_identity.mission_id.as_str(),
            execution_identity.logical_execution_key.as_str(),
            execution_identity.execution_id.as_str(),
            execution_identity.runtime_id.as_str(),
            execution_identity.runtime_version.as_str(),
            execution_identity.config_id.as_str(),
            execution_identity.evidence_ref.as_str(),
        ] {
            if value.trim().is_empty() {
                return Err(WorkloadIdentityAdmissionError::InvalidExecutionIdentity);
            }
        }
        if execution_identity.lease_generation == 0 || execution_identity.fencing_token == 0 {
            return Err(WorkloadIdentityAdmissionError::InvalidExecutionIdentity);
        }

        let expected_binding = RuntimeIdentityBinding {
            runtime_id: execution_identity.runtime_id.clone(),
            runtime_version: execution_identity.runtime_version.clone(),
            config_id: execution_identity.config_id.clone(),
        };
        self.validate_against_trust_configuration(
            &expected_binding,
            trust_configuration,
            now_epoch,
        )
    }
}
