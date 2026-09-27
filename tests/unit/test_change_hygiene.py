import unittest

from scripts.check_change_hygiene import (
    BudgetState,
    ChangeSnapshot,
    evaluate,
)


def snapshot(
    *,
    branch: str = "feat/issue-657-test",
    files: int = 5,
    additions: int = 100,
    deletions: int = 20,
    ahead: int = 1,
    behind: int = 0,
    clean: bool = True,
) -> ChangeSnapshot:
    return ChangeSnapshot(
        branch=branch,
        head_sha="a" * 40,
        base_ref="origin/main",
        base_sha="b" * 40,
        merge_base_sha="b" * 40,
        changed_files=files,
        additions=additions,
        deletions=deletions,
        ahead=ahead,
        behind=behind,
        worktree_clean=clean,
    )


class ChangeHygieneEvaluationTests(unittest.TestCase):
    def test_small_clean_change_passes(self):
        result = evaluate(snapshot(), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.PASS)

    def test_soft_file_trigger_warns(self):
        result = evaluate(snapshot(files=21), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.WARN)

    def test_soft_line_trigger_warns(self):
        result = evaluate(
            snapshot(additions=500, deletions=101),
            change_class="ORDINARY",
        )
        self.assertEqual(result.state, BudgetState.WARN)

    def test_ordinary_350_file_change_blocks(self):
        result = evaluate(snapshot(files=350), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.BLOCK)
        self.assertTrue(any("decompose" in reason for reason in result.reasons))

    def test_documentation_large_change_does_not_get_silent_exception(self):
        result = evaluate(
            snapshot(files=41),
            change_class="DOCUMENTATION",
            exception_id="issue-657",
        )
        self.assertEqual(result.state, BudgetState.BLOCK)

    def test_generated_large_change_requires_explicit_exception(self):
        without_exception = evaluate(snapshot(files=350), change_class="GENERATED")
        with_exception = evaluate(
            snapshot(files=350),
            change_class="GENERATED",
            exception_id="issue-657-generated",
        )
        self.assertEqual(without_exception.state, BudgetState.BLOCK)
        self.assertEqual(with_exception.state, BudgetState.WARN)

    def test_dirty_worktree_blocks_by_default(self):
        result = evaluate(snapshot(clean=False), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.BLOCK)

    def test_dirty_worktree_can_be_diagnostic_when_explicitly_allowed(self):
        result = evaluate(
            snapshot(clean=False),
            change_class="ORDINARY",
            require_clean=False,
        )
        self.assertEqual(result.state, BudgetState.PASS)

    def test_main_branch_blocks(self):
        result = evaluate(snapshot(branch="main"), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.BLOCK)

    def test_no_commits_ahead_blocks(self):
        result = evaluate(snapshot(ahead=0), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.BLOCK)

    def test_behind_base_warns_by_default(self):
        result = evaluate(snapshot(behind=2), change_class="ORDINARY")
        self.assertEqual(result.state, BudgetState.WARN)

    def test_behind_base_blocks_when_current_base_required(self):
        result = evaluate(
            snapshot(behind=2),
            change_class="ORDINARY",
            require_current_base=True,
        )
        self.assertEqual(result.state, BudgetState.BLOCK)


if __name__ == "__main__":
    unittest.main()
