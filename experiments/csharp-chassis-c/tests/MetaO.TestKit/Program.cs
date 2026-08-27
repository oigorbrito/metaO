using MetaO.Contracts;
using MetaO.Kernel;
using MetaO.Reconcile;
using MetaO.Budget;
using MetaORegistry = MetaO.Registry.Registry;
using MetaOControlPlane = MetaO.ControlPlane.ControlPlane;

namespace MetaO.TestKit;

internal static class AssertEx
{
    public static void True(bool condition, string name)
    {
        if (!condition) throw new Exception(name);
    }

    public static void Equal<T>(T expected, T actual, string name)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
        {
            throw new Exception($"{name}: expected {expected}, got {actual}");
        }
    }

    public static void Throws<T>(Action action, string name) where T : Exception
    {
        try
        {
            action();
            throw new Exception($"{name}: no exception");
        }
        catch (T)
        {
        }
    }
}

sealed class FakeA : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, Id, true);
}

sealed class FakeB : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("beta");
    public VersionId Version => VersionId.Create("1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, Id, true);
}

sealed class VersionedFake : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("2");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, Id, true);
}

sealed class ThrowingOrchestrator : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("panic");
    public VersionId Version => VersionId.Create("1");
    public ExecutionResult Execute(ExecutionRequest request) => throw new InvalidOperationException("panic");
}

internal static class Program
{
    private static ExecutionRequest Request(string orchestrator = "alpha") => new(
        MissionId.Create("mission-1"),
        OrchestratorId.Create(orchestrator),
        VersionId.Create("v1"),
        "evidence-1");

    private static EvidenceEnvelope Evidence(bool valid = true, string orchestrator = "alpha", string key = "evidence-1", long created = 10, long expires = 20) =>
        new(
            MissionId.Create("mission-1"),
            OrchestratorId.Create(orchestrator),
            VersionId.Create("v1"),
            key,
            "state-1",
            "policy-1",
            "digest-1",
            valid,
            created,
            expires);

    public static int Main()
    {
        var tests = new Action[]
        {
            () => AssertEx.Throws<ArgumentException>(() => MissionId.Create(""), "invalid mission"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), null, PolicyDecision.Allow, 15), "succeeded not accepted without evidence"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(valid: false), PolicyDecision.Allow, 15), "self report cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), PolicyDecision.Deny, 15), "deny overrides success"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(orchestrator: "beta"), PolicyDecision.Allow, 15), "mis-bound evidence"),
            () =>
            {
                var registry = new MetaORegistry();
                AssertEx.True(registry.Register(new FakeA()), "register fake a");
                AssertEx.True(!registry.Register(new FakeA()), "duplicate runtime id");
            },
            () =>
            {
                var registry = new MetaORegistry();
                registry.Register(new FakeA());
                AssertEx.Throws<InvalidOperationException>(() => registry.Register(new VersionedFake()), "version conflict");
            },
            () =>
            {
                var registry = new MetaORegistry();
                registry.Register(new ThrowingOrchestrator());
                var result = registry.ExecuteContained(OrchestratorId.Create("panic"), Request("panic"));
                AssertEx.True(!result.Succeeded, "runtime exception contained");
            },
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), false, "cancelled"), Evidence(), PolicyDecision.Allow, 15), "cancellation cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), false, "timeout"), Evidence(), PolicyDecision.Allow, 15), "timeout cannot mint acceptance"),
            () =>
            {
                var refs = typeof(AcceptanceKernel).Assembly.GetReferencedAssemblies().Select(a => a.Name).ToArray();
                AssertEx.True(!refs.Contains("Microsoft.AspNetCore.App"), "kernel must not reference aspnet");
                AssertEx.True(!refs.Contains("Microsoft.EntityFrameworkCore"), "kernel must not reference ef");
            },
            () =>
            {
                var registry = new MetaORegistry();
                var request = Request("beta");
                registry.Register(new FakeA());
                var outcome = MetaOControlPlane.ReplaceAndReconcile(registry, new FakeA(), new FakeB(), request, Evidence(orchestrator: "beta"), PolicyDecision.Allow, 15);
                AssertEx.Equal(AcceptanceDecision.Accept, outcome.Decision, "replacement acceptance");
                AssertEx.True(outcome.Reconciled, "replacement reconciled");
            },
            () =>
            {
                var desired = new[] { OrchestratorId.Create("alpha"), OrchestratorId.Create("beta") };
                var observed = new[] { OrchestratorId.Create("alpha") };
                var first = Reconciler.Missing(desired, observed);
                var second = Reconciler.Missing(desired, observed);
                AssertEx.Equal(first.Count, second.Count, "reconcile idempotent");
                AssertEx.Equal("beta", first[0].Value, "reconcile expected missing");
            },
            () =>
            {
                var budget = new AcceptanceBudget(1);
                AssertEx.True(budget.TryBeginSettlement("s1"), "first settlement begins");
                AssertEx.True(!budget.TryBeginSettlement("s2"), "second settlement oversubscribed");
                AssertEx.True(!budget.TryBeginSettlement("s2"), "settlement retry remains idempotent");
                AssertEx.True(budget.TryCompleteSettlement("s1"), "complete settlement");
                AssertEx.True(!budget.TryCompleteSettlement("s1"), "settlement retry idempotent");
            },
        };

        var failures = 0;
        for (var i = 0; i < tests.Length; i++)
        {
            try
            {
                tests[i]();
            }
            catch (Exception ex)
            {
                failures++;
                Console.Error.WriteLine($"FAIL {i + 1}: {ex.Message}");
            }
        }

        Console.WriteLine($"TEST_COUNT={tests.Length}");
        Console.WriteLine($"FAILURES={failures}");
        return failures == 0 ? 0 : 1;
    }
}
