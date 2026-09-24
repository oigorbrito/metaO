# SSH Git checkpoint transfer transaction contract

`SshGitRepositoryTransport.transfer_exact` is transport-only. Scheduler authority, checkpoint identity authority, and project acceptance remain outside the transport.

## Atomicity contract

Before mutation, the transport observes and validates a clean destination HEAD and retains that commit as the rollback checkpoint. Fetching the bundle may add Git objects but does not move the destination worktree HEAD.

Once `git reset --hard <authoritative-commit>` succeeds, any later transfer failure—including destination re-observation failure or remote temporary-bundle cleanup failure—causes a rollback attempt.

Rollback is deliberately conditional. The transport restores the previous HEAD only when all of the following remain true:

1. the destination is still a Git worktree;
2. the destination worktree is clean;
3. the current destination HEAD is exactly the commit applied by this transfer attempt;
4. the previously observed destination commit is still present and valid.

If any condition is false, rollback is refused rather than overwriting concurrent or unknown destination state. The operation remains failed and higher layers must treat the destination as requiring recovery/inspection.

After rollback, the transport re-observes a clean destination and requires the prior HEAD exactly. Rollback failure is surfaced as transfer failure and is never converted to success.

## Cleanup contract

The remote temporary bundle is always subject to cleanup. Cleanup failure is visible. If destination mutation already occurred, cleanup failure also triggers the same conditional rollback before the cleanup error is propagated. A leftover remote bundle is therefore never reported as a successful transfer.

## Evidence boundary

Successful return means the destination was observed clean at the exact authoritative commit and remote temporary cleanup completed. An exception means no transfer PASS may be inferred, even if some Git objects were fetched or a reset occurred temporarily.
