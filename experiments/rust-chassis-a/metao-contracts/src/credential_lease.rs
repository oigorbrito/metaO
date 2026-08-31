use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CredentialLeaseError {
    BlankField(&'static str),
    InvalidValidityWindow,
    InvalidRenewalBound,
    InvalidAssuranceStatusPair,
    InvalidEvidenceBasis,
    MissingRevocationEvidence,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CredentialLeaseAssurance {
    Brokered,
    DevelopmentStatic,
    Unsupported,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CredentialLeaseEvidenceBasis {
    BrokerVerified,
    DevelopmentLocal,
    CallerDeclared,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum CredentialRevocationStatus {
    Active,
    Revoked,
    RevocationUnknown,
    Expired,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CredentialLeaseBinding {
    pub runtime_id: String,
    pub workload_identity: String,
    pub runtime_config_id: String,
    pub mission_id: String,
    pub execution_id: String,
}

impl CredentialLeaseBinding {
    pub fn validate(&self) -> Result<(), CredentialLeaseError> {
        for (name, value) in [
            ("runtime_id", self.runtime_id.as_str()),
            ("workload_identity", self.workload_identity.as_str()),
            ("runtime_config_id", self.runtime_config_id.as_str()),
            ("mission_id", self.mission_id.as_str()),
            ("execution_id", self.execution_id.as_str()),
        ] {
            if value.trim().is_empty() {
                return Err(CredentialLeaseError::BlankField(name));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CredentialLease {
    pub lease_ref: String,
    pub binding: CredentialLeaseBinding,
    pub credential_class: String,
    pub target_service: String,
    pub policy_authority_ref: String,
    pub issued_at_epoch: i64,
    pub expires_at_epoch: i64,
    pub renewable: bool,
    pub max_expires_at_epoch: Option<i64>,
    pub assurance: CredentialLeaseAssurance,
    pub evidence_basis: CredentialLeaseEvidenceBasis,
    pub revocation_status: CredentialRevocationStatus,
    pub revocation_evidence_ref: Option<String>,
}

impl CredentialLease {
    pub fn validate(&self) -> Result<(), CredentialLeaseError> {
        self.binding.validate()?;
        for (name, value) in [
            ("lease_ref", self.lease_ref.as_str()),
            ("credential_class", self.credential_class.as_str()),
            ("target_service", self.target_service.as_str()),
            ("policy_authority_ref", self.policy_authority_ref.as_str()),
        ] {
            if value.trim().is_empty() {
                return Err(CredentialLeaseError::BlankField(name));
            }
        }
        if self.expires_at_epoch <= self.issued_at_epoch {
            return Err(CredentialLeaseError::InvalidValidityWindow);
        }

        match (self.renewable, self.max_expires_at_epoch) {
            (true, Some(max_expires))
                if max_expires > self.expires_at_epoch && max_expires > self.issued_at_epoch => {}
            (true, _) => return Err(CredentialLeaseError::InvalidRenewalBound),
            (false, None) => {}
            (false, Some(_)) => return Err(CredentialLeaseError::InvalidRenewalBound),
        }

        match self.assurance {
            CredentialLeaseAssurance::Brokered => {
                if self.evidence_basis != CredentialLeaseEvidenceBasis::BrokerVerified {
                    return Err(CredentialLeaseError::InvalidEvidenceBasis);
                }
            }
            CredentialLeaseAssurance::DevelopmentStatic => {
                if self.evidence_basis != CredentialLeaseEvidenceBasis::DevelopmentLocal {
                    return Err(CredentialLeaseError::InvalidEvidenceBasis);
                }
            }
            CredentialLeaseAssurance::Unsupported => {
                if self.revocation_status == CredentialRevocationStatus::Active {
                    return Err(CredentialLeaseError::InvalidAssuranceStatusPair);
                }
                if self.evidence_basis == CredentialLeaseEvidenceBasis::BrokerVerified {
                    return Err(CredentialLeaseError::InvalidEvidenceBasis);
                }
            }
        }

        if self.revocation_status == CredentialRevocationStatus::Revoked {
            if self.evidence_basis != CredentialLeaseEvidenceBasis::BrokerVerified {
                return Err(CredentialLeaseError::InvalidEvidenceBasis);
            }
            if self
                .revocation_evidence_ref
                .as_deref()
                .is_none_or(|value| value.trim().is_empty())
            {
                return Err(CredentialLeaseError::MissingRevocationEvidence);
            }
        }
        Ok(())
    }

    pub fn applies_to(&self, binding: &CredentialLeaseBinding, now_epoch: i64) -> bool {
        self.validate().is_ok()
            && &self.binding == binding
            && self.revocation_status == CredentialRevocationStatus::Active
            && now_epoch >= self.issued_at_epoch
            && now_epoch < self.expires_at_epoch
            && self.assurance != CredentialLeaseAssurance::Unsupported
    }

    pub fn can_renew_to(&self, requested_expires_at_epoch: i64, now_epoch: i64) -> bool {
        if !self.renewable || !self.applies_to(&self.binding, now_epoch) {
            return false;
        }
        if requested_expires_at_epoch <= self.expires_at_epoch {
            return false;
        }
        self.max_expires_at_epoch
            .is_some_and(|maximum| requested_expires_at_epoch <= maximum)
    }

    pub fn revocation_confirmed(&self) -> bool {
        self.validate().is_ok()
            && self.assurance == CredentialLeaseAssurance::Brokered
            && self.evidence_basis == CredentialLeaseEvidenceBasis::BrokerVerified
            && self.revocation_status == CredentialRevocationStatus::Revoked
            && self
                .revocation_evidence_ref
                .as_deref()
                .is_some_and(|value| !value.trim().is_empty())
    }
}
