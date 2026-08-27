using MetaO.Contracts;

namespace MetaO.Kernel;

public interface IOrchestrator
{
    OrchestratorId Id { get; }
    VersionId Version { get; }
    ExecutionResult Execute(ExecutionRequest request);
}

public static class AcceptanceKernel
{
    public static AcceptanceDecision Evaluate(
        ExecutionRequest request,
        ExecutionResult result,
        EvidenceEnvelope? evidence,
        AcceptanceTrustContext trust,
        AcceptanceBindingContext binding,
        PolicyDecision policy,
        long nowEpoch)
    {
        if (policy == PolicyDecision.Deny) return AcceptanceDecision.Block;
        if (!result.Succeeded) return AcceptanceDecision.NotDone;
        if (result.MissionId != request.MissionId ||
            result.ExecutionId != request.ExecutionId ||
            result.OrchestratorId != request.OrchestratorId ||
            result.AdapterVersion != request.AdapterVersion)
        {
            return AcceptanceDecision.Block;
        }
        if (evidence is null) return AcceptanceDecision.NotDone;
        if (!evidence.Value.Valid) return AcceptanceDecision.Block;
        if (evidence.Value.MissionId != request.MissionId ||
            evidence.Value.ExecutionId != request.ExecutionId ||
            evidence.Value.OrchestratorId != request.OrchestratorId ||
            evidence.Value.AdapterVersion != request.AdapterVersion)
        {
            return AcceptanceDecision.Stale;
        }
        if (evidence.Value.VerifierId != trust.TrustedVerifierId ||
            evidence.Value.ProvenanceRootId != trust.TrustedProvenanceRootId ||
            evidence.Value.AuthorityId != trust.AuthorizedAuthorityId)
        {
            return AcceptanceDecision.Block;
        }
        if (evidence.Value.EvidenceKey != request.EvidenceKey ||
            evidence.Value.EvidenceDigest is null ||
            evidence.Value.SubjectStateVersion != binding.ExpectedSubjectStateVersion ||
            evidence.Value.PolicyVersion != binding.ExpectedPolicyVersion.Value)
        {
            return AcceptanceDecision.Stale;
        }
        if (nowEpoch < evidence.Value.CreatedEpoch || nowEpoch > evidence.Value.ExpiresEpoch) return AcceptanceDecision.Stale;
        return AcceptanceDecision.Accept;
    }
}
