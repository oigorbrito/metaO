using MetaO.Contracts;

namespace MetaO.Registry;

public static class RuntimeGovernance
{
    public static RuntimeAuthorizationObservation? LatestAuthorization(
        OrchestratorId orchestratorId,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization)
    {
        RuntimeAuthorizationObservation? latest = null;
        foreach (var item in authorization)
        {
            if (item.OrchestratorId != orchestratorId)
            {
                continue;
            }

            if (latest is null ||
                item.Version > latest.Value.Version ||
                (item.Version == latest.Value.Version && item.ObservedEpoch > latest.Value.ObservedEpoch))
            {
                latest = item;
            }
        }

        return latest;
    }

    public static bool IsEligible(
        RuntimeHealthObservation health,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization,
        long currentEpoch)
    {
        if (health.State != RuntimeHealthState.Healthy || health.ObservedEpoch != currentEpoch)
        {
            return false;
        }

        var latest = LatestAuthorization(health.OrchestratorId, authorization);
        return latest is { } current &&
            current.State == RuntimeAuthorizationState.Active &&
            current.ObservedEpoch == currentEpoch;
    }

    public static OrchestratorId? SelectNext(
        IReadOnlyList<RuntimeHealthObservation> health,
        IReadOnlyList<RuntimeAuthorizationObservation> authorization,
        long currentEpoch,
        OrchestratorId? skip = null)
    {
        foreach (var item in health.OrderBy(x => x.Version).ThenBy(x => x.OrchestratorId.Value, StringComparer.Ordinal))
        {
            if (skip is { } skipped && item.OrchestratorId == skipped)
            {
                continue;
            }

            if (IsEligible(item, authorization, currentEpoch))
            {
                return item.OrchestratorId;
            }
        }

        return null;
    }
}
