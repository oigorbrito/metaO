namespace MetaO.Contracts;

public interface IIdentityValue
{
    string Value { get; }
    bool IsValid { get; }
}

public readonly struct MissionId : IEquatable<MissionId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private MissionId(string value) => _value = Validate(value, nameof(Value));
    public static MissionId Create(string value) => new(value);
    private static string Validate(string value, string name) =>
        !string.IsNullOrWhiteSpace(value) ? value.Trim() : throw new ArgumentException("Invalid identity.", name);
    public bool Equals(MissionId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is MissionId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(MissionId left, MissionId right) => left.Equals(right);
    public static bool operator !=(MissionId left, MissionId right) => !left.Equals(right);
}

public readonly struct OrchestratorId : IEquatable<OrchestratorId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private OrchestratorId(string value) => _value = MissionId.Create(value).Value;
    public static OrchestratorId Create(string value) => new(value);
    public bool Equals(OrchestratorId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is OrchestratorId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(OrchestratorId left, OrchestratorId right) => left.Equals(right);
    public static bool operator !=(OrchestratorId left, OrchestratorId right) => !left.Equals(right);
}

public readonly struct VersionId : IEquatable<VersionId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private VersionId(string value) => _value = MissionId.Create(value).Value;
    public static VersionId Create(string value) => new(value);
    public bool Equals(VersionId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is VersionId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(VersionId left, VersionId right) => left.Equals(right);
    public static bool operator !=(VersionId left, VersionId right) => !left.Equals(right);
}

public readonly struct ExecutionId : IEquatable<ExecutionId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private ExecutionId(string value) => _value = MissionId.Create(value).Value;
    public static ExecutionId Create(string value) => new(value);
    public bool Equals(ExecutionId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is ExecutionId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(ExecutionId left, ExecutionId right) => left.Equals(right);
    public static bool operator !=(ExecutionId left, ExecutionId right) => !left.Equals(right);
}

public readonly struct VerifierId : IEquatable<VerifierId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private VerifierId(string value) => _value = MissionId.Create(value).Value;
    public static VerifierId Create(string value) => new(value);
    public bool Equals(VerifierId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is VerifierId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(VerifierId left, VerifierId right) => left.Equals(right);
    public static bool operator !=(VerifierId left, VerifierId right) => !left.Equals(right);
}

public readonly struct ProvenanceRootId : IEquatable<ProvenanceRootId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private ProvenanceRootId(string value) => _value = MissionId.Create(value).Value;
    public static ProvenanceRootId Create(string value) => new(value);
    public bool Equals(ProvenanceRootId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is ProvenanceRootId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(ProvenanceRootId left, ProvenanceRootId right) => left.Equals(right);
    public static bool operator !=(ProvenanceRootId left, ProvenanceRootId right) => !left.Equals(right);
}

public readonly struct AuthorityId : IEquatable<AuthorityId>, IIdentityValue
{
    private readonly string? _value;
    public string Value => _value ?? throw new InvalidOperationException("Invalid identity.");
    public bool IsValid => !string.IsNullOrWhiteSpace(_value);
    private AuthorityId(string value) => _value = MissionId.Create(value).Value;
    public static AuthorityId Create(string value) => new(value);
    public bool Equals(AuthorityId other) => string.Equals(_value, other._value, StringComparison.Ordinal);
    public override bool Equals(object? obj) => obj is AuthorityId other && Equals(other);
    public override int GetHashCode() => StringComparer.Ordinal.GetHashCode(_value ?? string.Empty);
    public override string ToString() => Value;
    public static bool operator ==(AuthorityId left, AuthorityId right) => left.Equals(right);
    public static bool operator !=(AuthorityId left, AuthorityId right) => !left.Equals(right);
}

public readonly record struct ExecutionRequest(MissionId MissionId, ExecutionId ExecutionId, OrchestratorId OrchestratorId, VersionId AdapterVersion, string EvidenceKey);

public readonly record struct ExecutionResult(MissionId MissionId, ExecutionId ExecutionId, OrchestratorId OrchestratorId, VersionId AdapterVersion, bool Succeeded, string? Error = null);

public readonly record struct EvidenceEnvelope(
    MissionId MissionId,
    ExecutionId ExecutionId,
    OrchestratorId OrchestratorId,
    VersionId AdapterVersion,
    VerifierId VerifierId,
    ProvenanceRootId ProvenanceRootId,
    AuthorityId AuthorityId,
    string EvidenceKey,
    string SubjectStateVersion,
    string PolicyVersion,
    string EvidenceDigest,
    bool Valid,
    long CreatedEpoch,
    long ExpiresEpoch);

public readonly record struct AcceptanceTrustContext(
    VerifierId TrustedVerifierId,
    ProvenanceRootId TrustedProvenanceRootId,
    AuthorityId AuthorizedAuthorityId);

public readonly record struct AcceptanceBindingContext(VersionId ExpectedPolicyVersion, string ExpectedSubjectStateVersion);

public enum RuntimeHealthState { Healthy, Degraded, Unhealthy }

public readonly record struct RuntimeHealthObservation(
    OrchestratorId OrchestratorId,
    RuntimeHealthState State,
    long ObservedEpoch,
    long Version);

public enum PolicyDecision { Deny, Allow }
public enum AcceptanceDecision { Accept, NotDone, Stale, Block, RequireHuman }

public sealed record IdentityTransportDto(
    string MissionId,
    string ExecutionId,
    string OrchestratorId,
    string AdapterVersion,
    string VerifierId,
    string ProvenanceRootId,
    string AuthorityId);

public static class IdentityTransport
{
    public static IdentityTransportDto ToDto(
        MissionId missionId,
        ExecutionId executionId,
        OrchestratorId orchestratorId,
        VersionId adapterVersion,
        VerifierId verifierId,
        ProvenanceRootId provenanceRootId,
        AuthorityId authorityId) =>
        new(missionId.Value, executionId.Value, orchestratorId.Value, adapterVersion.Value, verifierId.Value, provenanceRootId.Value, authorityId.Value);

    public static (MissionId MissionId, ExecutionId ExecutionId, OrchestratorId OrchestratorId, VersionId AdapterVersion, VerifierId VerifierId, ProvenanceRootId ProvenanceRootId, AuthorityId AuthorityId) FromDto(IdentityTransportDto dto) =>
        (MissionId.Create(dto.MissionId), ExecutionId.Create(dto.ExecutionId), OrchestratorId.Create(dto.OrchestratorId), VersionId.Create(dto.AdapterVersion), VerifierId.Create(dto.VerifierId), ProvenanceRootId.Create(dto.ProvenanceRootId), AuthorityId.Create(dto.AuthorityId));
}
