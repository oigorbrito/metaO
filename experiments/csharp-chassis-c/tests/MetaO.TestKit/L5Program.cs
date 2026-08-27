using MetaO.Contracts;
using MetaO.ControlPlane;
using MetaO.Kernel;
using MetaO.Registry;
using MetaORegistry = MetaO.Registry.Registry;
using System.Text.Json;

namespace MetaO.TestKit;

sealed class ResumeFakeB : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("beta");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) =>
        new(request.MissionId, request.ExecutionId, Id, Version, true);
}

internal static class L5Program
{
    private const int BaselineCount = 69;

    private static ResumeCheckpoint Checkpoint(
        string policy = "policy-1",
        string state = "state-1",
        string nextAction = "execute") =>
        new(
            MissionId.Create("mission-1"),
            ExecutionId.Create("exec-1"),
            OrchestratorId.Create("beta"),
            VersionId.Create("v1"),
            "evidence-1",
            VersionId.Create(policy),
            state,
            ResumePhase.Execute,
            nextAction);

    private static EvidenceEnvelope Evidence(
        string policy = "policy-1",
        string state = "state-1") =>
        new(
            MissionId.Create("mission-1"),
            ExecutionId.Create("exec-1"),
            OrchestratorId.Create("beta"),
            VersionId.Create("v1"),
            VerifierId.Create("trusted-verifier"),
            ProvenanceRootId.Create("trusted-root"),
            AuthorityId.Create("trusted-authority"),
            "evidence-1",
            state,
            policy,
            "digest-1",
            true,
            10,
            20);

    private static AcceptanceTrustContext Trust() =>
        new(
            VerifierId.Create("trusted-verifier"),
            ProvenanceRootId.Create("trusted-root"),
            AuthorityId.Create("trusted-authority"));

    private static RuntimeHealthObservation Healthy(long epoch = 15) =>
        new(OrchestratorId.Create("beta"), RuntimeHealthState.Healthy, epoch, 1);

    private static RuntimeHealthObservation Degraded(long epoch = 15) =>
        new(OrchestratorId.Create("beta"), RuntimeHealthState.Degraded, epoch, 1);

    private static RuntimeAuthorizationObservation Active(long version = 1, long epoch = 15) =>
        new(OrchestratorId.Create("beta"), RuntimeAuthorizationState.Active, epoch, version);

    private static RuntimeAuthorizationObservation Revoked(long version = 2, long epoch = 15) =>
        new(OrchestratorId.Create("beta"), RuntimeAuthorizationState.Revoked, epoch, version);

    private static ResumeCheckpoint RoundTrip(ResumeCheckpoint checkpoint)
    {
        var dto = ResumeCheckpointTransport.ToDto(checkpoint);
        var json = JsonSerializer.Serialize(dto);
        var parsed = JsonSerializer.Deserialize<ResumeCheckpointDto>(json)!;
        return ResumeCheckpointTransport.FromDto(parsed);
    }

    private static ResumeOutcome Resume(
        ResumeCheckpoint checkpoint,
        RuntimeHealthObservation health,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization,
        EvidenceEnvelope? evidence = null)
    {
        var restartedRegistry = new MetaORegistry();
        restartedRegistry.Register(new ResumeFakeB());
        return ResumeCoordinator.Resume(
            checkpoint,
            restartedRegistry,
            health,
            authorization,
            evidence ?? Evidence(),
            Trust(),
            PolicyDecision.Allow,
            15);
    }

    public static int Main()
    {
        var baselineResult = Program.Main();

        var tests = new Action[]
        {
            () =>
            {
                var before = Checkpoint();
                var after = RoundTrip(before);
                AssertEx.Equal(before.MissionId, after.MissionId, "checkpoint mission round trip");
                AssertEx.Equal(before.ExecutionId, after.ExecutionId, "checkpoint execution round trip");
                AssertEx.Equal(before.OrchestratorId, after.OrchestratorId, "checkpoint orchestrator round trip");
                AssertEx.Equal(before.AdapterVersion, after.AdapterVersion, "checkpoint adapter round trip");
                AssertEx.Equal(before.EvidenceKey, after.EvidenceKey, "checkpoint evidence key round trip");
                AssertEx.Equal(before.ExpectedPolicyVersion, after.ExpectedPolicyVersion, "checkpoint policy round trip");
                AssertEx.Equal(before.ExpectedSubjectStateVersion, after.ExpectedSubjectStateVersion, "checkpoint state round trip");
                AssertEx.Equal(before.Phase, after.Phase, "checkpoint phase round trip");
                AssertEx.Equal(before.NextAction, after.NextAction, "next action survives restart");
            },
            () =>
            {
                var dto = ResumeCheckpointTransport.ToDto(Checkpoint(nextAction: "accept"));
                AssertEx.Throws<ArgumentException>(() => ResumeCheckpointTransport.FromDto(dto), "checkpoint cannot persist accept");
            },
            () =>
            {
                var beforeRestart = Checkpoint();
                var resumedCheckpoint = RoundTrip(beforeRestart);
                var outcome = Resume(resumedCheckpoint, Healthy(), new[] { Active() });
                AssertEx.Equal(beforeRestart.NextAction, resumedCheckpoint.NextAction, "restart next action stable");
                AssertEx.True(outcome.Executed, "restart resumes execution");
                AssertEx.Equal(AcceptanceDecision.Accept, outcome.Decision, "restart active runtime accepted");
                AssertEx.Equal("complete", outcome.NextAction, "resume completes only after revalidation");
            },
            () =>
            {
                var resumedCheckpoint = RoundTrip(Checkpoint(policy: "policy-2"));
                var outcome = Resume(resumedCheckpoint, Healthy(), new[] { Active() }, Evidence(policy: "policy-1"));
                AssertEx.Equal(AcceptanceDecision.Stale, outcome.Decision, "resume revalidates policy");
            },
            () =>
            {
                var resumedCheckpoint = RoundTrip(Checkpoint(state: "state-2"));
                var outcome = Resume(resumedCheckpoint, Healthy(), new[] { Active() }, Evidence(state: "state-1"));
                AssertEx.Equal(AcceptanceDecision.Stale, outcome.Decision, "resume revalidates state");
            },
            () =>
            {
                AssertEx.True(RuntimeGovernance.IsEligible(Healthy(), new[] { Active() }, 15), "healthy active selectable");
                AssertEx.True(!RuntimeGovernance.IsEligible(Healthy(), new[] { Revoked() }, 15), "healthy revoked not selectable");
            },
            () =>
            {
                var authorization = new[] { Active(version: 1), Revoked(version: 2) };
                AssertEx.True(!RuntimeGovernance.IsEligible(Healthy(), authorization, 15), "newer revoked overrides active");
                AssertEx.Equal(RuntimeAuthorizationState.Revoked, RuntimeGovernance.LatestAuthorization(OrchestratorId.Create("beta"), authorization)!.Value.State, "revoked is current authorization");
            },
            () =>
            {
                AssertEx.True(!RuntimeGovernance.IsEligible(Degraded(), new[] { Active() }, 15), "degraded active follows degraded policy");
            },
            () =>
            {
                var checkpoint = Checkpoint();
                var runtime = new ResumeFakeB();
                var result = runtime.Execute(new ExecutionRequest(checkpoint.MissionId, checkpoint.ExecutionId, checkpoint.OrchestratorId, checkpoint.AdapterVersion, checkpoint.EvidenceKey));
                AssertEx.True(result.Succeeded, "runtime succeeded before revocation");
                var decision = ResumeCoordinator.EvaluateCompleted(
                    checkpoint,
                    result,
                    Healthy(),
                    new[] { Active(version: 1), Revoked(version: 2) },
                    Evidence(),
                    Trust(),
                    PolicyDecision.Allow,
                    15);
                AssertEx.Equal(AcceptanceDecision.Block, decision, "revoked success cannot accept");
            },
            () =>
            {
                var serializedCheckpoint = RoundTrip(Checkpoint());
                var authorizationAfterRestart = new[] { Active(version: 1), Revoked(version: 2) };
                var outcome = Resume(serializedCheckpoint, Healthy(), authorizationAfterRestart);
                AssertEx.True(!outcome.Executed, "revoked checkpoint runtime must not execute");
                AssertEx.Equal(AcceptanceDecision.Block, outcome.Decision, "revoked checkpoint cannot accept");
                AssertEx.Equal("require_replan", outcome.NextAction, "revoked checkpoint requires replan");
            }
        };

        var l5Failures = 0;
        for (var i = 0; i < tests.Length; i++)
        {
            try
            {
                tests[i]();
            }
            catch (Exception ex)
            {
                l5Failures++;
                Console.Error.WriteLine($"L5_FAIL {i + 1}: {ex.Message}");
            }
        }

        var directFailures = l5Failures + (baselineResult == 0 ? 0 : 1);
        Console.WriteLine($"L5_TEST_COUNT={tests.Length}");
        Console.WriteLine($"DIRECT_COUNT={BaselineCount + tests.Length}");
        Console.WriteLine($"DIRECT_FAILURES={directFailures}");
        Console.WriteLine($"RESTART_CHECKPOINT_ROUNDTRIP={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"RESTART_RESUME={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"RESUME_REVALIDATES_POLICY={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"RESUME_REVALIDATES_STATE={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"RESUME_REVALIDATES_GOVERNANCE={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"REVOKED_RUNTIME_NOT_SELECTED={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"REVOCATION_OVERRIDES_HEALTH={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"HEALTHY_NOT_EQUAL_AUTHORIZED={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"REVOKED_SUCCESS_NOT_ACCEPTED={(l5Failures == 0 ? "PASS" : "FAIL")}");
        Console.WriteLine($"RESUME_REVOKED_RUNTIME={(l5Failures == 0 ? "PASS" : "FAIL")}");
        return directFailures == 0 ? 0 : 1;
    }
}
