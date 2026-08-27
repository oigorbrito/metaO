using MetaO.Contracts;
using MetaO.Kernel;

namespace MetaO.Registry;

public enum RegistryError { Duplicate, VersionConflict, Missing, Panicked }

public sealed class Registry
{
    private readonly Dictionary<OrchestratorId, IOrchestrator> _items = new();

    public bool Register(IOrchestrator orchestrator)
    {
        if (_items.TryGetValue(orchestrator.Id, out var existing))
        {
            if (existing.Version != orchestrator.Version) throw new InvalidOperationException("VersionConflict");
            return false;
        }
        _items.Add(orchestrator.Id, orchestrator);
        return true;
    }

    public bool Unregister(OrchestratorId id) => _items.Remove(id);

    public ExecutionResult ExecuteContained(OrchestratorId id, ExecutionRequest request)
    {
        if (!_items.TryGetValue(id, out var orchestrator)) throw new KeyNotFoundException("Missing");
        if (orchestrator.Version != request.AdapterVersion)
        {
            return new ExecutionResult(request.MissionId, request.ExecutionId, id, request.AdapterVersion, false, "VersionMismatch");
        }
        try
        {
            return orchestrator.Execute(request);
        }
        catch (Exception ex)
        {
            return new ExecutionResult(request.MissionId, request.ExecutionId, id, request.AdapterVersion, false, ex.Message);
        }
    }
}
