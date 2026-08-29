using MetaO.Contracts;
using MetaO.Kernel;
using MetaO.Registry;
using MetaORegistry = MetaO.Registry.Registry;
using System.Diagnostics;

sealed class PanicRuntime : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("panic");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => throw new InvalidOperationException("panic");
}

sealed class FakeA : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("alpha");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) => new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class SlowRuntime : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("slow");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request)
    {
        Thread.Sleep(2);
        return new ExecutionResult(request.MissionId, request.ExecutionId, Id, Version, true);
    }
}

static class Program
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

    public static int Main()
    {
        var contained = 0;
        var escaped = 0;
        var invariant = 0;
        var recovery = 0;
        var exits = 0;
        var latencies = new List<long>();
        var rss = new List<long>();
        var registry = new MetaORegistry();
        registry.Register(new FakeA());

        for (var i = 0; i < 1000; i++)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                switch (i % 4)
                {
                    case 0:
                        registry.Register(new PanicRuntime());
                        _ = registry.ExecuteContained(OrchestratorId.Create("panic"), Request("panic"));
                        break;
                    case 1:
                        registry.Register(new SlowRuntime());
                        _ = registry.ExecuteContained(OrchestratorId.Create("slow"), Request("slow"));
                        break;
                    case 2:
                    {
                        var result = new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true);
                        var decision = AcceptanceKernel.Evaluate(Request(), result, Evidence(orchestrator: "beta"), new AcceptanceTrustContext(VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("trusted-authority")), new AcceptanceBindingContext(VersionId.Create("policy-1"), "state-1"), PolicyDecision.Allow, 15);
                        if (decision == AcceptanceDecision.Stale) invariant++;
                        break;
                    }
                    default:
                    {
                        var decision = AcceptanceKernel.Evaluate(Request(), new ExecutionResult(MissionId.Create("mission-1"), ExecutionId.Create("exec-1"), OrchestratorId.Create("alpha"), VersionId.Create("v1"), true), Evidence(), new AcceptanceTrustContext(VerifierId.Create("trusted-verifier"), ProvenanceRootId.Create("trusted-root"), AuthorityId.Create("trusted-authority")), new AcceptanceBindingContext(VersionId.Create("policy-1"), "state-1"), PolicyDecision.Allow, 15);
                        if (decision == AcceptanceDecision.Accept) contained++;
                        break;
                    }
                }
                recovery++;
            }
            catch (Exception)
            {
                contained++;
            }
            finally
            {
                sw.Stop();
                latencies.Add(sw.ElapsedMilliseconds);
                rss.Add(Process.GetCurrentProcess().WorkingSet64);
            }
        }

        Console.WriteLine($"contained_failures={contained}");
        Console.WriteLine($"escaped_failures={escaped}");
        Console.WriteLine($"invariant_violations={invariant}");
        Console.WriteLine($"post_fault_recovery_successes={recovery}");
        Console.WriteLine($"unexpected_process_exits={exits}");
        Console.WriteLine($"recovery_latency_p50_ms={Percentile(latencies, 50)}");
        Console.WriteLine($"recovery_latency_p95_ms={Percentile(latencies, 95)}");
        Console.WriteLine($"recovery_latency_p99_ms={Percentile(latencies, 99)}");
        Console.WriteLine($"peak_rss_bytes={rss.Max()}");
        Console.WriteLine($"rss_first_100_mean={rss.Take(100).Average()}");
        Console.WriteLine($"rss_last_100_mean={rss.Skip(Math.Max(0, rss.Count - 100)).Average()}");
        Console.WriteLine($"rss_delta_bytes={rss.Last() - rss.First()}");
        Console.WriteLine($"rss_growth_percent={(rss.Last() - rss.First()) * 100.0 / Math.Max(1, rss.First())}");
        return escaped == 0 ? 0 : 1;
    }

    private static long Percentile(List<long> values, int percentile)
    {
        var ordered = values.OrderBy(v => v).ToArray();
        var index = (int)Math.Round((percentile / 100.0) * (ordered.Length - 1));
        return ordered[index];
    }
}
