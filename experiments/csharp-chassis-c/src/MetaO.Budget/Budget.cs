namespace MetaO.Budget;

public sealed class AcceptanceBudget
{
    private readonly object _gate = new();
    private readonly HashSet<string> _settled = new(StringComparer.Ordinal);
    private readonly HashSet<string> _inFlight = new(StringComparer.Ordinal);
    public int MaxConcurrentSettlements { get; }
    public int CurrentConcurrentSettlements { get; private set; }
    public int OversubscriptionAttempts { get; private set; }

    public AcceptanceBudget(int maxConcurrentSettlements)
    {
        MaxConcurrentSettlements = maxConcurrentSettlements > 0 ? maxConcurrentSettlements : throw new ArgumentOutOfRangeException(nameof(maxConcurrentSettlements));
    }

    public bool TryBeginSettlement(string settlementId)
    {
        lock (_gate)
        {
            if (_settled.Contains(settlementId) || _inFlight.Contains(settlementId))
            {
                return false;
            }

            if (CurrentConcurrentSettlements >= MaxConcurrentSettlements)
            {
                OversubscriptionAttempts++;
                return false;
            }

            _inFlight.Add(settlementId);
            CurrentConcurrentSettlements++;
            return true;
        }
    }

    public bool TryCompleteSettlement(string settlementId)
    {
        lock (_gate)
        {
            if (!_inFlight.Remove(settlementId))
            {
                return false;
            }

            if (!_settled.Add(settlementId))
            {
                return false;
            }

            CurrentConcurrentSettlements = Math.Max(0, CurrentConcurrentSettlements - 1);
            return true;
        }
    }
}
