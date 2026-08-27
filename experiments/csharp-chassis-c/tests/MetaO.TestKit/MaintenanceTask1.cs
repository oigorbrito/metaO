using System.Runtime.CompilerServices;
using MetaO.Contracts;

namespace MetaO.TestKit;

internal static class MaintenanceTask1
{
    [ModuleInitializer]
    internal static void Run()
    {
        var original = AttemptId.Create("attempt-1");
        var roundTrip = AttemptId.Create(original.Value);
        if (original != roundTrip || roundTrip.Value != "attempt-1")
        {
            throw new InvalidOperationException("AttemptId round trip failed.");
        }

        var rejected = false;
        try
        {
            _ = AttemptId.Create("   ");
        }
        catch (ArgumentException)
        {
            rejected = true;
        }

        if (!rejected)
        {
            throw new InvalidOperationException("AttemptId accepted an empty identity.");
        }

        Console.WriteLine("MAINT_TASK1_IDENTITY=PASS");
    }
}
