using System.Runtime.CompilerServices;
using MetaO.Contracts;
using MetaO.Kernel;

namespace MetaO.TestKit;

internal static class MaintenanceTask2
{
    [ModuleInitializer]
    internal static void Run()
    {
        var invalid = new EvidenceEnvelope(
            MissionId.Create("mission-1"),
            ExecutionId.Create("exec-1"),
            OrchestratorId.Create("alpha"),
            VersionId.Create("v1"),
            VerifierId.Create("verifier-1"),
            ProvenanceRootId.Create("root-1"),
            AuthorityId.Create("authority-1"),
            "evidence-1",
            "state-1",
            "policy-1",
            "digest-1",
            false,
            10,
            20);

        if (AcceptanceKernel.ClassifyRejection(invalid) != RejectionReason.InvalidEvidence)
        {
            throw new InvalidOperationException("Invalid evidence did not propagate the explicit rejection reason.");
        }
        if (AcceptanceKernel.ClassifyRejection(null) is not null)
        {
            throw new InvalidOperationException("Missing evidence was incorrectly classified as invalid evidence.");
        }

        Console.WriteLine("MAINT_TASK2_REJECTION=PASS");
    }
}
