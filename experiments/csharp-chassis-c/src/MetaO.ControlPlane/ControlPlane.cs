using MetaO.Contracts;
using MetaO.Kernel;
using MetaORegistry = MetaO.Registry.Registry;
using MetaO.Reconcile;

namespace MetaO.ControlPlane;

public sealed record ControlPlaneOutcome(AcceptanceDecision Decision, bool Reconciled);

public static class ControlPlane
{
    public static ControlPlaneOutcome ReplaceAndReconcile(
        MetaORegistry registry,
        IOrchestrator current,
        IOrchestrator replacement,
        ExecutionRequest request,
        EvidenceEnvelope? evidence,
        AcceptanceTrustContext trust,
        PolicyDecision policy,
        long nowEpoch)
    {
        registry.Unregister(current.Id);
        registry.Register(replacement);
        var result = registry.ExecuteContained(replacement.Id, request);
        var decision = AcceptanceKernel.Evaluate(request, result, evidence, trust, policy, nowEpoch);
        return new ControlPlaneOutcome(decision, true);
    }
}
