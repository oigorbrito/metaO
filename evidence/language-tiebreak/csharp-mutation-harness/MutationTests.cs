using MetaO.Contracts;
using MetaO.Kernel;
using MetaO.Registry;
using MetaOControlPlane = MetaO.ControlPlane.ControlPlane;
using MetaORegistry = MetaO.Registry.Registry;

namespace MutationHarness;

public sealed class FakeA : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

public sealed class FakeB : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("beta");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

public sealed class VersionedFake : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("v2");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

public class MutationTests
{
    private static ExecutionRequest Request(string orchestrator = "alpha") => new(
        MissionId.Create("mission-1"),
        ExecutionId.Create("exec-1"),
        OrchestratorId.Create(orchestrator),
        VersionId.Create("v1"),
        "evidence-1");

    private static EvidenceEnvelope Evidence(string orchestrator = "alpha", string authority = "trusted-authority") => new(
        MissionId.Create("mission-1"),
        ExecutionId.Create("exec-1"),
        OrchestratorId.Create(orchestrator),
        VersionId.Create("v1"),
        VerifierId.Create("trusted-verifier"),
        ProvenanceRootId.Create("trusted-root"),
        AuthorityId.Create(authority),
        "evidence-1",
        "state-1",
        "policy-1",
        "digest-1",
        true,
        10,
        20);

    private static AcceptanceTrustContext Trust(string authority = "trusted-authority") =>
        new(
            VerifierId.Create("trusted-verifier"),
            ProvenanceRootId.Create("trusted-root"),
            AuthorityId.Create(authority));

    private static AcceptanceBindingContext Binding(string policy = "policy-1", string state = "state-1") =>
        new(VersionId.Create(policy), state);

    [Fact]
    public void DenyPrecedence()
    {
        var result = new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true);
        Assert.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), result, Evidence(), Trust(), Binding(), PolicyDecision.Deny, 15));
    }

    [Fact]
    public void EvidenceBinding()
    {
        var result = new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true);
        Assert.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(Request(), result, Evidence(orchestrator: "beta"), Trust(), Binding(), PolicyDecision.Allow, 15));
    }

    [Fact]
    public void AuthorityAndProvenance()
    {
        var result = new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true);
        Assert.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), result, Evidence(authority: "untrusted-authority"), Trust(), Binding(), PolicyDecision.Allow, 15));
        Assert.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), result, Evidence(), Trust(authority: "untrusted-authority"), Binding(), PolicyDecision.Allow, 15));
    }

    [Fact]
    public void SucceededIsNotAcceptedWithoutEvidence()
    {
        var result = new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true);
        Assert.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), result, null, Trust(), Binding(), PolicyDecision.Allow, 15));
    }

    [Fact]
    public void IdentityAndVersionConflict()
    {
        var registry = new MetaORegistry();
        registry.Register(new FakeA());
        Assert.False(registry.Register(new FakeA()));
        Assert.Throws<InvalidOperationException>(() => registry.Register(new VersionedFake()));
    }

    [Fact]
    public void ReplacementAndFailoverStillRespectAcceptance()
    {
        var registry = new MetaORegistry();
        registry.Register(new FakeA());
        var outcome = MetaOControlPlane.ReplaceAndReconcile(registry, new FakeA(), new FakeB(), Request("beta"), Evidence(orchestrator: "beta"), Trust(), Binding(), PolicyDecision.Allow, 15);
        Assert.Equal(AcceptanceDecision.Accept, outcome.Decision);
    }
}
