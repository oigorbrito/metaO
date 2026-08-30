use serde::{Deserialize, Serialize};

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
    InvalidAttestedCredential,
    InvalidAssuranceCredentialPair,
    InvalidValidityWindow,
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

        if let (Some(issued), Some(expires)) = (self.issued_at_epoch, self.expires_at_epoch) {
            if expires <= issued {
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
                if self
                    .trust_root_ref
                    .as_deref()
                    .map_or(true, |value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankTrustRootRef);
                }
                if self
                    .credential_ref
                    .as_deref()
                    .map_or(true, |value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankCredentialRef);
                }
                if self
                    .verifier_provenance
                    .as_deref()
                    .map_or(true, |value| value.trim().is_empty())
                {
                    return Err(WorkloadIdentityError::BlankVerifierProvenance);
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
        if self.assurance != WorkloadIdentityAssurance::Attested {
            return false;
        }
        if let Some(issued) = self.issued_at_epoch {
            if now_epoch < issued {
                return false;
            }
        }
        if let Some(expires) = self.expires_at_epoch {
            if now_epoch >= expires {
                return false;
            }
        }
        true
    }

    pub fn applies_to(&self, runtime_id: &str, runtime_version: &str, config_id: &str) -> bool {
        self.binding.runtime_id == runtime_id
            && self.binding.runtime_version == runtime_version
            && self.binding.config_id == config_id
    }
}
