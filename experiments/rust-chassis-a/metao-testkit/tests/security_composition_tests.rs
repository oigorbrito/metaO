use metao_contracts::workload_identity::{WorkloadIdentity, AssuranceLevel};
use metao_contracts::runtime_security::{
    RuntimeSecurityFacts, SecurityRequirementProfile, evaluate_runtime_security
};
use metao_contracts::credential_lease::{CredentialLease, LeaseStatus};
use metao_contracts::runtime_certification::{RuntimeCertification, CertificationStatus};

#[test]
fn test_security_assurance_boundaries() {
    let identity = WorkloadIdentity {
        runtime_name: "test-runtime".into(),
        assurance: AssuranceLevel::Development, // Scenario S2: Development identity
        trust_root: None,
    };
    
    let facts = RuntimeSecurityFacts {
        identity,
        certified: false,
    };
    
    let profile = SecurityRequirementProfile {
        require_attested: true,
        require_certified: true,
    };
    
    // Evaluate security
    let evaluation = evaluate_runtime_security(&facts, &profile);
    assert!(!evaluation.is_admitted());
    
    // We compose the rest in a test to prove the scenarios (already done mostly in the tests for each module)
}
