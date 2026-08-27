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
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class FakeB : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("beta");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class DegradedFake : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("gamma");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class VersionedFake : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("v2");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class ThrowingOrchestrator : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("panic");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => throw new InvalidOperationException("panic");
}

internal static class Program
{
    private static ExecutionRequest Request(string orchestrator = "alpha") => new(
        MissionId.Create("mission-1"),
        ExecutionId.Create("exec-1"),
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
        string execution = "exec-1",
        long created = 10,
        long expires = 20) =>
        new(
            MissionId.Create("mission-1"),
            ExecutionId.Create(execution),
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

    private static AcceptanceBindingContext Binding(string policy = "policy-1", string subject = "state-1") =>
        new(VersionId.Create(policy), subject);

    private static RuntimeHealthObservation Health(string orchestrator, RuntimeHealthState state, long version, long observedEpoch = 15) =>
        new(OrchestratorId.Create(orchestrator), state, observedEpoch, version);

    private static bool IsEligible(RuntimeHealthObservation observation, long currentEpoch) =>
        observation.State == RuntimeHealthState.Healthy && observation.ObservedEpoch == currentEpoch;

    private static OrchestratorId SelectNext(IReadOnlyList<RuntimeHealthObservation> health, long currentEpoch, string? skip = null)
    {
        foreach (var item in health.OrderBy(x => x.Version).ThenBy(x => x.OrchestratorId.Value, StringComparer.Ordinal))
        {
            if (item.ObservedEpoch != currentEpoch)
            {
                continue;
            }

            if (skip is not null && item.OrchestratorId.Value == skip)
            {
                continue;
            }

            if (IsEligible(item, currentEpoch))
            {
                return item.OrchestratorId;
            }
        }

        return OrchestratorId.Create("none");
    }

    private static (string Plan, OrchestratorId Selected) ReplanAfterFailure(IReadOnlyList<RuntimeHealthObservation> health, long currentEpoch, string failed)
    {
        var selected = SelectNext(health, currentEpoch, failed);
        var plan = selected.Value == "none" ? "require_replan" : $"select:{selected.Value}";
        return (plan, selected);
    }

    private static IdentityTransportDto IdentityDto(
        string mission = "mission-1",
        string execution = "exec-1",
        string orchestrator = "alpha",
        string version = "v1",
        string verifier = "trusted-verifier",
        string provenance = "trusted-root",
        string authority = "trusted-authority") =>
        new(mission, execution, orchestrator, version, verifier, provenance, authority);

    private static (MissionId MissionId, ExecutionId ExecutionId, OrchestratorId OrchestratorId, VersionId AdapterVersion, VerifierId VerifierId, ProvenanceRootId ProvenanceRootId, AuthorityId AuthorityId) RoundTripTransport(IdentityTransportDto dto)
    {
        var json = JsonSerializer.Serialize(dto);
        var parsed = JsonSerializer.Deserialize<IdentityTransportDto>(json)!;
        return IdentityTransport.FromDto(parsed);
    }

    private static T RoundTrip<T>(T value)
    {
        var json = JsonSerializer.Serialize(value);
        return JsonSerializer.Deserialize<T>(json)!;
    }

    private static string RepoRoot()
    {
        var current = AppContext.BaseDirectory;
        while (!File.Exists(Path.Combine(current, "MetaO.ChassisC.sln")))
        {
            var parent = Directory.GetParent(current);
            if (parent is null)
            {
                throw new DirectoryNotFoundException("Unable to locate MetaO.ChassisC.sln");
            }
            current = parent.FullName;
        }

        return current;
    }

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
            Binding(),
            PolicyDecision.Allow,
            15);
    }

    public static int Main()
    {
        var tests = new Action[]
        {
            () => AssertEx.Throws<ArgumentException>(() => MissionId.Create(""), "invalid mission"),
            () => AssertEx.Throws<ArgumentException>(() => MissionId.Create(" "), "mission whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => ExecutionId.Create(" "), "execution whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => OrchestratorId.Create(" "), "orchestrator whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => VersionId.Create(" "), "version whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => VerifierId.Create(" "), "verifier whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => ProvenanceRootId.Create(" "), "provenance whitespace"),
            () => AssertEx.Throws<ArgumentException>(() => AuthorityId.Create(" "), "authority whitespace"),
            () => AssertEx.True(!default(MissionId).IsValid, "mission default invalid"),
            () => AssertEx.True(!default(ExecutionId).IsValid, "execution default invalid"),
            () => AssertEx.True(!default(OrchestratorId).IsValid, "orchestrator default invalid"),
            () => AssertEx.True(!default(VersionId).IsValid, "version default invalid"),
            () => AssertEx.True(!default(VerifierId).IsValid, "verifier default invalid"),
            () => AssertEx.True(!default(ProvenanceRootId).IsValid, "provenance default invalid"),
            () => AssertEx.True(!default(AuthorityId).IsValid, "authority default invalid"),
            () =>
            {
                var dto = IdentityDto();
                var round = RoundTripTransport(dto);
                AssertEx.Equal(dto.MissionId, round.MissionId.Value, "transport mission round trip");
                AssertEx.Equal(dto.ExecutionId, round.ExecutionId.Value, "transport execution round trip");
                AssertEx.Equal(dto.OrchestratorId, round.OrchestratorId.Value, "transport orchestrator round trip");
                AssertEx.Equal(dto.AdapterVersion, round.AdapterVersion.Value, "transport version round trip");
                AssertEx.Equal(dto.VerifierId, round.VerifierId.Value, "transport verifier round trip");
                AssertEx.Equal(dto.ProvenanceRootId, round.ProvenanceRootId.Value, "transport provenance round trip");
                AssertEx.Equal(dto.AuthorityId, round.AuthorityId.Value, "transport authority round trip");
            },
            () => AssertEx.Throws<ArgumentException>(() => IdentityTransport.FromDto(IdentityDto(mission: "")), "empty transport rejected"),
            () => AssertEx.Throws<ArgumentException>(() => IdentityTransport.FromDto(IdentityDto(execution: " ")), "whitespace transport rejected"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), null, Trust(), Binding(), PolicyDecision.Allow, 15), "succeeded not accepted without evidence"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), new EvidenceEnvelope(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("untrusted-authority"), "evidence-1", "state-1", "policy-1", "digest-1", true, 10, 20), Trust(), Binding(), PolicyDecision.Allow, 15), "self report cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(), Binding(), PolicyDecision.Deny, 15), "deny overrides success"),
            () => AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(orchestrator: "beta"), Trust(), Binding(), PolicyDecision.Allow, 15), "mis-bound evidence"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), false, "none"), null, Trust(), Binding(), PolicyDecision.Allow, 15), "python golden not done"),
            () => AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(), Binding(), PolicyDecision.Allow, 15), "python golden accept"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(verifier: "evil-verifier"), Trust(), Binding(), PolicyDecision.Allow, 15), "python golden block"),
            () => AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(created: 10, expires: 14), Trust(), Binding(), PolicyDecision.Allow, 15), "python golden stale"),
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
            () =>
            {
                AssertEx.True(IsEligible(Health("alpha", RuntimeHealthState.Healthy, 1), 15), "healthy eligible");
                AssertEx.True(!IsEligible(Health("beta", RuntimeHealthState.Unhealthy, 1), 15), "unhealthy not eligible");
                AssertEx.True(!IsEligible(Health("gamma", RuntimeHealthState.Degraded, 1), 15), "degraded not healthy");
            },
            () => AssertEx.True(IsEligible(Health("alpha", RuntimeHealthState.Healthy, 1), 15), "healthy current observation selectable"),
            () => AssertEx.True(!IsEligible(Health("beta", RuntimeHealthState.Degraded, 1), 15), "degraded current observation not selectable"),
            () => AssertEx.True(!IsEligible(Health("gamma", RuntimeHealthState.Unhealthy, 1), 15), "unhealthy current observation not selectable"),
            () => AssertEx.True(!IsEligible(Health("delta", RuntimeHealthState.Healthy, 1, 14), 15), "stale healthy observation not selectable"),
            () =>
            {
                var health = new[]
                {
                    Health("alpha", RuntimeHealthState.Degraded, 1),
                    Health("beta", RuntimeHealthState.Unhealthy, 2),
                    Health("gamma", RuntimeHealthState.Healthy, 3),
                };
                AssertEx.Equal("gamma", SelectNext(health, 15).Value, "failover picks tertiary");
            },
            () =>
            {
                var attempt1 = new ThrowingOrchestrator();
                var secondary = Health("beta", RuntimeHealthState.Unhealthy, 2);
                var tertiary = Health("gamma", RuntimeHealthState.Healthy, 3);
                var health = new[] { Health("alpha", RuntimeHealthState.Healthy, 1), secondary, tertiary };
                var plan = ReplanAfterFailure(health, 15, "alpha");
                AssertEx.Equal("select:gamma", plan.Plan, "replan after failure");
                AssertEx.Equal("gamma", plan.Selected.Value, "replan selects healthy tertiary");
                var registry = new MetaORegistry();
                registry.Register(attempt1);
                AssertEx.True(!registry.ExecuteContained(attempt1.Id, Request("panic")).Succeeded, "primary failure contained");
                AssertEx.True(!IsEligible(secondary, 15), "secondary skipped because unhealthy");
            },
            () =>
            {
                var health = new[]
                {
                    Health("alpha", RuntimeHealthState.Degraded, 1),
                    Health("beta", RuntimeHealthState.Unhealthy, 2),
                    Health("gamma", RuntimeHealthState.Unhealthy, 3),
                };
                var plan = ReplanAfterFailure(health, 15, "alpha");
                AssertEx.Equal("require_replan", plan.Plan, "all runtimes fail");
                AssertEx.Equal("none", plan.Selected.Value, "no acceptance when all fail");
            },
            () =>
            {
                var health = new[]
                {
                    Health("alpha", RuntimeHealthState.Degraded, 1),
                    Health("beta", RuntimeHealthState.Unhealthy, 2),
                    Health("gamma", RuntimeHealthState.Healthy, 3),
                };
                AssertEx.Equal("gamma", SelectNext(health, 15).Value, "order skips degraded and unhealthy");
            },
            () =>
            {
                var health = new[]
                {
                    Health("alpha", RuntimeHealthState.Degraded, 1),
                    Health("beta", RuntimeHealthState.Unhealthy, 2),
                    Health("gamma", RuntimeHealthState.Healthy, 3, 14),
                };
                AssertEx.Equal("none", SelectNext(health, 15).Value, "stale healthy requires replan");
                AssertEx.Equal("require_replan", ReplanAfterFailure(health, 15, "alpha").Plan, "stale healthy replan");
            },
            () =>
            {
                var observed = Health("beta", RuntimeHealthState.Unhealthy, 1, 15);
                var next = Health("beta", RuntimeHealthState.Healthy, 2, 16);
                AssertEx.True(!IsEligible(observed, 16), "stale health rejected");
                AssertEx.True(IsEligible(next, 16), "recovery converges");
                AssertEx.True(!IsEligible(observed, 16), "recovery is idempotent on stale report");
            },
            () =>
            {
                var registry = new MetaORegistry();
                var active = new FakeA();
                var revoked = new FakeB();
                registry.Register(active);
                registry.Register(revoked);
                registry.Unregister(revoked.Id);
                var request = Request("alpha");
                var selected = registry.ExecuteContained(active.Id, request);
                AssertEx.True(selected.Succeeded, "restart/resume active runtime succeeds");
                AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(request, selected, Evidence(), Trust(), Binding(), PolicyDecision.Allow, 15), "resume revalidates governance");
            },
            () =>
            {
                var registry = new MetaORegistry();
                var revoked = new FakeB();
                registry.Register(revoked);
                registry.Unregister(revoked.Id);
                AssertEx.Throws<KeyNotFoundException>(() => registry.ExecuteContained(revoked.Id, Request("beta")), "revoked runtime not selected");
            },
            () =>
            {
                var budget = new AcceptanceBudget(1);
                var begin = new[]
                {
                    Task.Run(() => budget.TryBeginSettlement("c1")),
                    Task.Run(() => budget.TryBeginSettlement("c2")),
                };
                Task.WaitAll(begin);
                AssertEx.True(begin.Count(t => t.Result) == 1, "concurrent budget atomicity");
            },
            () =>
            {
                var budget = new AcceptanceBudget(2);
                AssertEx.True(budget.TryBeginSettlement("s1"), "first settlement begins");
                AssertEx.True(budget.TryCompleteSettlement("s1"), "first settlement completes");
                AssertEx.True(!budget.TryCompleteSettlement("s1"), "same settlement idempotent");
                AssertEx.True(!budget.TryBeginSettlement("s1"), "same settlement cannot restart after completion");
            },
            () =>
            {
                var evidence = Evidence(execution: "exec-1", created: 10, expires: 20);
                var replay = Evidence(execution: "exec-1", created: 10, expires: 20);
                AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), replay, Trust(), Binding(policy: "policy-2"), PolicyDecision.Allow, 15), "out of order evidence rejected");
                AssertEx.Equal(evidence, replay, "replay evidence is structurally identical");
            },
            () =>
            {
                var registry = new MetaORegistry();
                registry.Register(new ThrowingOrchestrator());
                var result = registry.ExecuteContained(OrchestratorId.Create("panic"), Request("panic"));
                AssertEx.True(!result.Succeeded, "malicious runtime reports contained");
                AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request("panic"), result, Evidence(orchestrator: "panic", authority: "untrusted-authority"), Trust(), Binding(), PolicyDecision.Allow, 15), "malicious runtime report rejected");
            },
            () =>
            {
                var trustedEvidence = Evidence(orchestrator: "beta", authority: "trusted-authority");
                var fallback = new FakeB();
                var fallbackResult = fallback.Execute(Request("beta"));
                AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request("beta"), fallbackResult, Evidence(orchestrator: "beta", authority: "untrusted-authority"), Trust(), Binding(), PolicyDecision.Allow, 15), "failover self-mint blocked");
                AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(Request("beta"), fallbackResult, trustedEvidence, Trust(), Binding(), PolicyDecision.Allow, 15), "failover with trusted evidence accepted");
            },
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), false, "cancelled"), Evidence(), Trust(), Binding(), PolicyDecision.Allow, 15), "cancellation cannot mint acceptance"),
            () => AssertEx.Equal(AcceptanceDecision.NotDone, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), false, "timeout"), Evidence(), Trust(), Binding(), PolicyDecision.Allow, 15), "timeout cannot mint acceptance"),
            () =>
            {
                var refs = typeof(AcceptanceKernel).Assembly.GetReferencedAssemblies().Select(a => a.Name).ToArray();
                AssertEx.True(!refs.Contains("Microsoft.AspNetCore.App"), "kernel must not reference aspnet");
                AssertEx.True(!refs.Contains("Microsoft.EntityFrameworkCore"), "kernel must not reference ef");
            },
            () =>
            {
                var request = Request();
                var evidence = Evidence();
                var dto = IdentityTransport.ToDto(
                    request.MissionId,
                    request.ExecutionId,
                    request.OrchestratorId,
                    request.AdapterVersion,
                    evidence.VerifierId,
                    evidence.ProvenanceRootId,
                    evidence.AuthorityId);
                var round = RoundTripTransport(dto);
                AssertEx.Equal(dto.MissionId, round.MissionId.Value, "request mission transport round trip");
                AssertEx.Equal(dto.ExecutionId, round.ExecutionId.Value, "request execution transport round trip");
                AssertEx.Equal(dto.OrchestratorId, round.OrchestratorId.Value, "request orchestrator transport round trip");
                AssertEx.Equal(dto.AdapterVersion, round.AdapterVersion.Value, "request version transport round trip");
                AssertEx.Equal(dto.VerifierId, round.VerifierId.Value, "trust verifier transport round trip");
                AssertEx.Equal(dto.ProvenanceRootId, round.ProvenanceRootId.Value, "trust provenance transport round trip");
                AssertEx.Equal(dto.AuthorityId, round.AuthorityId.Value, "trust authority transport round trip");
            },
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-2"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true),
                Evidence(execution: "exec-2"),
                Trust(),
                Binding(),
                PolicyDecision.Allow,
                15), "execution binding blocks cross-execution evidence"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-2"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true),
                Evidence(),
                Trust(),
                Binding(),
                PolicyDecision.Allow,
                15), "result mission binding blocks mismatch"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("beta"), VersionId.Create("v1"), true),
                Evidence(orchestrator: "beta"),
                Trust(),
                Binding(),
                PolicyDecision.Allow,
                15), "result runtime binding blocks mismatch"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v2"), true),
                Evidence(),
                Trust(),
                Binding(),
                PolicyDecision.Allow,
                15), "result adapter binding blocks mismatch"),
            () => AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true),
                Evidence(created: 10, expires: 20),
                Trust(),
                Binding(policy: "policy-2"),
                PolicyDecision.Allow,
                15), "policy version binding blocks mismatch"),
            () => AssertEx.Equal(AcceptanceDecision.Stale, AcceptanceKernel.Evaluate(
                Request(),
                new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true),
                Evidence(created: 10, expires: 20),
                Trust(),
                Binding(subject: "state-2"),
                PolicyDecision.Allow,
                15), "subject state binding forces stale"),
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
                var outcome = MetaOControlPlane.ReplaceAndReconcile(registry, new FakeA(), new FakeB(), request, Evidence(orchestrator: "beta"), Trust(), Binding(), PolicyDecision.Allow, 15);
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
            () =>
            {
                var budget = new AcceptanceBudget(4);
                var begins = Enumerable.Range(0, 32).Select(_ => Task.Run(() => budget.TryBeginSettlement("same"))).ToArray();
                Task.WaitAll(begins);
                AssertEx.True(begins.Count(t => t.Result) == 1, "same-id begin succeeds once");
                AssertEx.True(budget.CurrentConcurrentSettlements == 1, "same-id begin reserves in-flight");
                var completes = Enumerable.Range(0, 32).Select(_ => Task.Run(() => budget.TryCompleteSettlement("same"))).ToArray();
                Task.WaitAll(completes);
                AssertEx.True(completes.Count(t => t.Result) == 1, "same-id complete succeeds once");
                AssertEx.True(budget.CurrentConcurrentSettlements == 0, "same-id completion releases once");
                AssertEx.True(!budget.TryBeginSettlement("same"), "same-id cannot restart after completion");
            },
            () => AssertEx.Equal(AcceptanceDecision.Accept, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(), Binding(), PolicyDecision.Allow, 15), "trusted verifier provenance authority accept"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(verifier: "untrusted"), Binding(), PolicyDecision.Allow, 15), "unknown verifier blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(provenance: "untrusted-root"), Binding(), PolicyDecision.Allow, 15), "untrusted provenance blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), Trust(authority: "untrusted-authority"), Binding(), PolicyDecision.Allow, 15), "unauthorized authority blocked"),
            () => AssertEx.Equal(AcceptanceDecision.Block, AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), new EvidenceEnvelope(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("untrusted-authority"), "evidence-1", "state-1", "policy-1", "digest-1", true, 10, 20), Trust(), Binding(), PolicyDecision.Allow, 15), "runtime self-mint blocked"),
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
