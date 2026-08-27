using MetaO.Contracts;
using MetaO.Kernel;
using MetaO.Registry;
using MetaORegistry = MetaO.Registry.Registry;

namespace MetaO.ControlPlane;

public sealed record ResumeOutcome(
    AcceptanceDecision Decision,
    string NextAction,
    bool Executed,
    OrchestratorId OrchestratorId);

public static class ResumeCoordinator
{
    public static AcceptanceDecision EvaluateCompleted(
        ResumeCheckpoint checkpoint,
        ExecutionResult result,
        RuntimeHealthObservation health,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization,
        EvidenceEnvelope? evidence,
        AcceptanceTrustContext trust,
        PolicyDecision policy,
        long nowEpoch)
    {
        if (!RuntimeGovernance.IsEligible(health, authorization, nowEpoch))
        {
            return AcceptanceDecision.Block;
        }

        var request = ToRequest(checkpoint);
        var binding = new AcceptanceBindingContext(
            checkpoint.ExpectedPolicyVersion,
            checkpoint.ExpectedSubjectStateVersion);
        return AcceptanceKernel.Evaluate(request, result, evidence, trust, binding, policy, nowEpoch);
    }

    public static ResumeOutcome Resume(
        ResumeCheckpoint checkpoint,
        MetaORegistry registry,
        RuntimeHealthObservation health,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization,
        EvidenceEnvelope? evidence,
        AcceptanceTrustContext trust,
        PolicyDecision policy,
        long nowEpoch)
    {
        if (health.OrchestratorId != checkpoint.OrchestratorId ||
            !RuntimeGovernance.IsEligible(health, authorization, nowEpoch))
        {
            return new ResumeOutcome(
                AcceptanceDecision.Block,
                "require_replan",
                false,
                checkpoint.OrchestratorId);
        }

        var request = ToRequest(checkpoint);
        var result = registry.ExecuteContained(checkpoint.OrchestratorId, request);
        var decision = EvaluateCompleted(
            checkpoint,
            result,
            health,
            authorization,
            evidence,
            trust,
            policy,
            nowEpoch);

        var nextAction = decision switch
        {
            AcceptanceDecision.Accept => "complete",
            AcceptanceDecision.Stale => "refresh_evidence",
            AcceptanceDecision.NotDone => "retry",
            AcceptanceDecision.RequireHuman => "require_human",
            _ => "block"
        };

        return new ResumeOutcome(decision, nextAction, true, checkpoint.OrchestratorId);
    }

    private static ExecutionRequest ToRequest(ResumeCheckpoint checkpoint) =>
        new(
            checkpoint.MissionId,
            checkpoint.ExecutionId,
            checkpoint.OrchestratorId,
            checkpoint.AdapterVersion,
            checkpoint.EvidenceKey);
}
