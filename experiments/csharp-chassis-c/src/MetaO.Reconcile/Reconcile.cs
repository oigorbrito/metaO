using MetaO.Contracts;

namespace MetaO.Reconcile;

public static class Reconciler
{
    public static IReadOnlyList<OrchestratorId> Missing(IReadOnlyCollection<OrchestratorId> desired, IReadOnlyCollection<OrchestratorId> observed)
    {
        var missing = desired.Where(d => !observed.Contains(d)).Distinct().OrderBy(x => x.Value, StringComparer.Ordinal).ToArray();
        return missing;
    }
}
