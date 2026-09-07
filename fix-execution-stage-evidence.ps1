$path = 'C:\Projetos\metao-gate\.worktrees\execution-stage-evidence\experiments\rust-chassis-a\metao-contracts\src\execution_stage_evidence.rs'
$text = [IO.File]::ReadAllText($path)
$text = [regex]::Replace(
    $text,
    '(?s)    let count = \|status\| \{\r?\n        ordered\r?\n            \.iter\(\)\r?\n            \.filter\(\|stage\| stage\.status == status\)\r?\n            \.count\(\)\r?\n    \};',
    @'
    let passed = ordered
        .iter()
        .filter(|stage| stage.status == ExecutionStageStatus::Pass)
        .count();
    let failed = ordered
        .iter()
        .filter(|stage| stage.status == ExecutionStageStatus::Failed)
        .count();
    let blocked = ordered
        .iter()
        .filter(|stage| stage.status == ExecutionStageStatus::Blocked)
        .count();
    let skipped = ordered
        .iter()
        .filter(|stage| stage.status == ExecutionStageStatus::Skipped)
        .count();
    let not_requested = ordered
        .iter()
        .filter(|stage| stage.status == ExecutionStageStatus::NotRequested)
        .count();
'@
)
$text = $text.Replace(
    '        passed: count(ExecutionStageStatus::Pass),`r`n        failed: count(ExecutionStageStatus::Failed),`r`n        blocked: count(ExecutionStageStatus::Blocked),`r`n        skipped: count(ExecutionStageStatus::Skipped),`r`n        not_requested: count(ExecutionStageStatus::NotRequested),',
    "        passed,`r`n        failed,`r`n        blocked,`r`n        skipped,`r`n        not_requested,"
)
[IO.File]::WriteAllText($path, $text)
