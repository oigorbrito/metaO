namespace MetaO.Contracts;

public enum RuntimeAuthorizationState
{
    Active,
    Revoked
}

public readonly record struct RuntimeAuthorizationObservation(
    OrchestratorId OrchestratorId,
    RuntimeAuthorizationState State,
    long ObservedEpoch,
    long Version);

public enum ResumePhase
{
    Execute,
    Verify,
    Replan
}

public readonly record struct ResumeCheckpoint(
    MissionId MissionId,
    ExecutionId ExecutionId,
    OrchestratorId OrchestratorId,
    VersionId AdapterVersion,
    string EvidenceKey,
    VersionId ExpectedPolicyVersion,
    string ExpectedSubjectStateVersion,
    ResumePhase Phase,
    string NextAction);

public sealed record ResumeCheckpointDto(
    string MissionId,
    string ExecutionId,
    string OrchestratorId,
    string AdapterVersion,
    string EvidenceKey,
    string ExpectedPolicyVersion,
    string ExpectedSubjectStateVersion,
    string Phase,
    string NextAction);

public static class ResumeCheckpointTransport
{
    public static ResumeCheckpointDto ToDto(ResumeCheckpoint checkpoint) =>
        new(
            checkpoint.MissionId.Value,
            checkpoint.ExecutionId.Value,
            checkpoint.OrchestratorId.Value,
            checkpoint.AdapterVersion.Value,
            checkpoint.EvidenceKey,
            checkpoint.ExpectedPolicyVersion.Value,
            checkpoint.ExpectedSubjectStateVersion,
            checkpoint.Phase.ToString(),
            checkpoint.NextAction);

    public static ResumeCheckpoint FromDto(ResumeCheckpointDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.EvidenceKey)) throw new ArgumentException("Invalid evidence key.", nameof(dto));
        if (string.IsNullOrWhiteSpace(dto.ExpectedSubjectStateVersion)) throw new ArgumentException("Invalid subject state version.", nameof(dto));
        if (string.IsNullOrWhiteSpace(dto.NextAction)) throw new ArgumentException("Invalid next action.", nameof(dto));
        if (string.Equals(dto.NextAction.Trim(), "accept", StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Checkpoint cannot persist ACCEPT.", nameof(dto));
        }
        if (!Enum.TryParse<ResumePhase>(dto.Phase, ignoreCase: false, out var phase))
        {
            throw new ArgumentException("Invalid resume phase.", nameof(dto));
        }

        return new ResumeCheckpoint(
            MissionId.Create(dto.MissionId),
            ExecutionId.Create(dto.ExecutionId),
            OrchestratorId.Create(dto.OrchestratorId),
            VersionId.Create(dto.AdapterVersion),
            dto.EvidenceKey.Trim(),
            VersionId.Create(dto.ExpectedPolicyVersion),
            dto.ExpectedSubjectStateVersion.Trim(),
            phase,
            dto.NextAction.Trim());
    }
}
