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
        PolicyDecision policy,
        long nowEpoch)
    {
        if (policy == PolicyDecision.Deny) return AcceptanceDecision.Block;
        if (!result.Succeeded) return AcceptanceDecision.NotDone;
        if (evidence is null) return AcceptanceDecision.NotDone;
        if (!evidence.Value.Valid) return AcceptanceDecision.Block;
        if (evidence.Value.MissionId != request.MissionId ||
            evidence.Value.OrchestratorId != request.OrchestratorId ||
            evidence.Value.AdapterVersion != request.AdapterVersion ||
            evidence.Value.EvidenceKey != request.EvidenceKey ||
            evidence.Value.EvidenceDigest is null ||
            evidence.Value.SubjectStateVersion is null ||
            evidence.Value.PolicyVersion is null)
        {
            return AcceptanceDecision.Block;
        }
        if (nowEpoch < evidence.Value.CreatedEpoch || nowEpoch > evidence.Value.ExpiresEpoch) return AcceptanceDecision.Stale;
        return AcceptanceDecision.Accept;
    }
}
