using MetaO.Contracts;
using MetaO.Kernel;
using MetaO.Reconcile;
using MetaO.Budget;
using MetaORegistry = MetaO.Registry.Registry;
using MetaOControlPlane = MetaO.ControlPlane.ControlPlane;
using System.Text.Json;
using System.IO;

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

    private static EvidenceEnvelope Evidence(
        bool valid = true,
        string orchestrator = "alpha",
        string key = "evidence-1",
        string verifier = "trusted-verifier",
        string provenance = "trusted-root",
        string authority = "trusted-authority",
        long created = 10,
        long expires = 20) =>
        new(
            MissionId.Create("mission-1"),
            OrchestratorId.Create(orchestrator),
            VersionId.Create("v1"),
            VerifierId.Create(verifier),
            ProvenanceRootId.Create(provenance),
            AuthorityId.Create(authority),
            key,
            "state-1",
            "policy-1",
            "digest-1",
            valid,
            created,
            expires);

    private static AcceptanceTrustContext Trust(
        string verifier = "trusted-verifier",
        string provenance = "trusted-root",
        string authority = "trusted-authority") =>
        new(
            VerifierId.Create(verifier),
            ProvenanceRootId.Create(provenance),
            AuthorityId.Create(authority));

    private static T RoundTrip<T>(T value)
    {
        var json = JsonSerializer.Serialize(value);
        return JsonSerializer.Deserialize<T>(json)!;
    }

    private static string RepoRoot() => Directory.GetCurrentDirectory();

    private static string ReadRepoFile(params string[] relativeSegments) => File.ReadAllText(Path.Combine(RepoRoot(), Path.Combine(relativeSegments)));

    private static void AssertNoForbiddenSource(string relativePath, params string[] forbidden)
    {
        var text = ReadRepoFile(relativePath);
        foreach (var item in forbidden)
        {
            AssertEx.True(!text.Contains(item, StringComparison.Ordinal), $"{relativePath} must not contain {item}");
        }
    }

    private static void AssertProjectHasNoForbiddenPackages(string relativePath)
    {
        var text = ReadRepoFile(relativePath);
        AssertEx.True(!text.Contains("PackageReference", StringComparison.Ordinal), $"{relativePath} must not add package refs");
        AssertEx.True(!text.Contains("EF Core", StringComparison.Ordinal), $"{relativePath} must not mention EF Core");
        AssertEx.True(!text.Contains("ABP", StringComparison.Ordinal), $"{relativePath} must not mention ABP");
        AssertEx.True(!text.Contains("workflow", StringComparison.OrdinalIgnoreCase), $"{relativePath} must not mention workflow");
        AssertEx.True(!text.Contains("durable", StringComparison.OrdinalIgnoreCase), $"{relativePath} must not mention durable");
        AssertEx.True(!text.Contains("event store", StringComparison.OrdinalIgnoreCase), $"{relativePath} must not mention event store");
        AssertEx.True(!text.Contains("background-job", StringComparison.OrdinalIgnoreCase), $"{relativePath} must not mention background-job");
    }

    private static AcceptanceDecision FailoverToFallback()
    {
        var primary = new ThrowingOrchestrator();
        var fallback = new FakeB();
        var registry = new MetaORegistry();
        registry.Register(primary);
        var primaryRequest = Request("panic");
        var primaryResult = registry.ExecuteContained(primary.Id, primaryRequest);
        if (primaryResult.Succeeded)
        {
            return AcceptanceDecision.Block;
        }

        registry.Unregister(primary.Id);
        registry.Register(fallback);
        var fallbackRequest = Request("beta");
        var fallbackResult = registry.ExecuteContained(fallback.Id, fallbackRequest);
        return AcceptanceKernel.Evaluate(
            fallbackRequest,
            fallbackResult,
            Evidence(orchestrator: "beta"),
            Trust(),
            PolicyDecision.Allow,
            15);
    }

    public static int Main()
    {
        var tests = new Action[]
        {
            () => AssertEx.Throws<ArgumentException>(() => MissionId.Create(""), "invalid mission"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), null, Trust(), PolicyDecision.Allow, 15), "succeeded not accepted without evidence"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), new EvidenceEnvelope(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("untrusted-authority"), "evidence-1", "state-1", "policy-1", "digest-1", true, 10, 20), Trust(), PolicyDecision.Allow, 15), "self report cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(), PolicyDecision.Deny, 15), "deny overrides success"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(orchestrator: "beta"), Trust(), PolicyDecision.Allow, 15), "mis-bound evidence"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), false, "none"), null, Trust(), PolicyDecision.Allow, 15), "python golden not done"),
            () => AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(), PolicyDecision.Allow, 15), "python golden accept"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(verifier: "evil-verifier"), Trust(), PolicyDecision.Allow, 15), "python golden block"),
            () => AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(created: 10, expires: 14), Trust(), PolicyDecision.Allow, 15), "python golden stale"),
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
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), false, "cancelled"), Evidence(), Trust(), PolicyDecision.Allow, 15), "cancellation cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), false, "timeout"), Evidence(), Trust(), PolicyDecision.Allow, 15), "timeout cannot mint acceptance"),
            () =>
            {
                var refs = typeof(AcceptanceKernel).Assembly.GetReferencedAssemblies().Select(a => a.Name).ToArray();
                AssertEx.True(!refs.Contains("Microsoft.AspNetCore.App"), "kernel must not reference aspnet");
                AssertEx.True(!refs.Contains("Microsoft.EntityFrameworkCore"), "kernel must not reference ef");
            },
            () =>
            {
                var request = Request();
                var result = new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true, "ok");
                var evidence = Evidence();
                var trust = Trust();
                AssertEx.Equal(request, RoundTrip(request), "request round trip");
                AssertEx.Equal(result, RoundTrip(result), "result round trip");
                AssertEx.Equal(evidence, RoundTrip(evidence), "evidence round trip");
                AssertEx.Equal(trust, RoundTrip(trust), "trust round trip");
            },
            () =>
            {
                AssertEx.Equal("AcceptanceKernel", typeof(AcceptanceKernel).Name, "acceptance kernel type");
                AssertNoForbiddenSource("src/MetaO.Registry/Registry.cs", "AcceptanceDecision", "Evaluate(", "PolicyDecision");
                AssertNoForbiddenSource("src/MetaO.Reconcile/Reconcile.cs", "AcceptanceDecision", "Evaluate(", "PolicyDecision");
                AssertNoForbiddenSource("src/MetaO.Budget/Budget.cs", "AcceptanceDecision", "Evaluate(", "PolicyDecision");
                var controlPlane = ReadRepoFile("src/MetaO.ControlPlane/ControlPlane.cs");
                AssertEx.True(controlPlane.Contains("AcceptanceKernel.Evaluate", StringComparison.Ordinal), "control plane delegates to kernel");
                AssertEx.True(!controlPlane.Contains("return AcceptanceDecision", StringComparison.Ordinal), "control plane must not mint acceptance");
            },
            () =>
            {
                AssertProjectHasNoForbiddenPackages("src/MetaO.Contracts/MetaO.Contracts.csproj");
                AssertProjectHasNoForbiddenPackages("src/MetaO.Kernel/MetaO.Kernel.csproj");
                AssertProjectHasNoForbiddenPackages("src/MetaO.Registry/MetaO.Registry.csproj");
                AssertProjectHasNoForbiddenPackages("src/MetaO.Reconcile/MetaO.Reconcile.csproj");
                AssertProjectHasNoForbiddenPackages("src/MetaO.ControlPlane/MetaO.ControlPlane.csproj");
                AssertProjectHasNoForbiddenPackages("src/MetaO.Budget/MetaO.Budget.csproj");
            },
            () =>
            {
                var registry = new MetaORegistry();
                var request = Request("beta");
                registry.Register(new FakeA());
                var outcome = MetaOControlPlane.ReplaceAndReconcile(registry, new FakeA(), new FakeB(), request, Evidence(orchestrator: "beta"), Trust(), PolicyDecision.Allow, 15);
                AssertEx.Equal(AcceptanceDecision.Accept, outcome.Decision, "replacement acceptance");
                AssertEx.True(outcome.Reconciled, "replacement reconciled");
            },
            () => AssertEx.Equal(AcceptanceDecision.Accept, FailoverToFallback(), "runtime failure can fail over to fallback runtime"),
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
            () => AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(), PolicyDecision.Allow, 15), "trusted verifier provenance authority accept"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(verifier: "untrusted"), PolicyDecision.Allow, 15), "unknown verifier blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(provenance: "untrusted-root"), PolicyDecision.Allow, 15), "untrusted provenance blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), Evidence(), Trust(authority: "untrusted-authority"), PolicyDecision.Allow, 15), "unauthorized authority blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), true), new EvidenceEnvelope(MissionId.Create("mission-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("untrusted-authority"), "evidence-1", "state-1", "policy-1", "digest-1", true, 10, 20), Trust(), PolicyDecision.Allow, 15), "runtime self-mint blocked"),
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
