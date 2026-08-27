using System.Runtime.CompilerServices;
using MetaO.Contracts;
using MetaO.Kernel;
using MetaORegistry = MetaO.Registry.Registry;

namespace MetaO.TestKit;

sealed class MaintenanceLegacyAdapter : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("swap-runtime");
    public VersionId Version => VersionId.Create("v1");
    public ExecutionResult Execute(ExecutionRequest request) =>
        new(request.MissionId, request.ExecutionId, Id, Version, true);
}

sealed class MaintenanceReplacementAdapter : IOrchestrator
{
    public OrchestratorId Id => OrchestratorId.Create("swap-runtime");
    public VersionId Version => VersionId.Create("v2");
    public ExecutionResult Execute(ExecutionRequest request) =>
        new(request.MissionId, request.ExecutionId, Id, Version, false, "replacement-behavior");
}

internal static class MaintenanceTask3
{
    [ModuleInitializer]
    internal static void Run()
    {
        var requestV1 = new ExecutionRequest(
            MissionId.Create("maint-mission-1"),
            ExecutionId.Create("maint-exec-1"),
            OrchestratorId.Create("swap-runtime"),
            VersionId.Create("v1"),
            "maint-evidence");

        var registry = new MetaORegistry();
        if (!registry.Register(new MaintenanceLegacyAdapter()))
        {
            throw new InvalidOperationException("Legacy adapter registration failed.");
        }
        var before = registry.ExecuteContained(OrchestratorId.Create("swap-runtime"), requestV1);
        if (!before.Succeeded)
        {
            throw new InvalidOperationException("Legacy adapter behavior was not observed.");
        }

        if (!registry.Unregister(OrchestratorId.Create("swap-runtime")))
        {
            throw new InvalidOperationException("Legacy adapter removal failed.");
        }
        if (!registry.Register(new MaintenanceReplacementAdapter()))
        {
            throw new InvalidOperationException("Replacement adapter registration failed.");
        }

        var requestV2 = requestV1 with { AdapterVersion = VersionId.Create("v2") };
        var after = registry.ExecuteContained(OrchestratorId.Create("swap-runtime"), requestV2);
        if (after.Succeeded || after.Error != "replacement-behavior")
        {
            throw new InvalidOperationException("Replacement adapter behavior was not observed.");
        }

        Console.WriteLine("MAINT_TASK3_ADAPTER_SWAP=PASS");
    }
}
