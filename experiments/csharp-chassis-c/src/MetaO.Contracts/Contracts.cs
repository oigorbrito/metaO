namespace MetaO.Contracts;

public readonly record struct MissionId(string Value)
{
    public static MissionId Create(string value) => new(Validate(value, nameof(Value)));
    private static string Validate(string value, string name) =>
        !string.IsNullOrWhiteSpace(value) ? value.Trim() : throw new ArgumentException("Invalid identity.", name);
}

public readonly record struct OrchestratorId(string Value)
{
    public static OrchestratorId Create(string value) => new(MissionId.Create(value).Value);
}

public readonly record struct VersionId(string Value)
{
    public static VersionId Create(string value) => new(MissionId.Create(value).Value);
}

public readonly record struct ExecutionRequest(MissionId MissionId, OrchestratorId OrchestratorId, VersionId AdapterVersion, string EvidenceKey);

public readonly record struct ExecutionResult(MissionId MissionId, OrchestratorId OrchestratorId, bool Succeeded, string? Error = null);

public readonly record struct EvidenceEnvelope(
    MissionId MissionId,
    OrchestratorId OrchestratorId,
    VersionId AdapterVersion,
    string EvidenceKey,
    string SubjectStateVersion,
    string PolicyVersion,
    string EvidenceDigest,
    bool Valid,
    long CreatedEpoch,
    long ExpiresEpoch);

public enum PolicyDecision { Deny, Allow }
public enum AcceptanceDecision { Accept, NotDone, Stale, Block, RequireHuman }
