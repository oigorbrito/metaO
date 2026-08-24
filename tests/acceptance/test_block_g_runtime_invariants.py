import importlib


def _runtime():
    return importlib.import_module("metao.runtime")


def test_block_g_lease_and_fencing_contract_exists():
    runtime = _runtime()
    assert hasattr(runtime, "Lease")
    assert hasattr(runtime, "FencingToken")


def test_block_g_stale_worker_rejection_exists():
    runtime = _runtime()
    assert hasattr(runtime, "reject_stale_worker")


def test_block_g_event_idempotency_exists():
    runtime = _runtime()
    assert hasattr(runtime, "IdempotencyKey")
    assert hasattr(runtime, "deduplicate_event")


def test_block_g_concurrency_and_replay_guard_exists():
    runtime = _runtime()
    assert hasattr(runtime, "ConcurrencyGuard")
    assert hasattr(runtime, "ReplayGuard")


def test_block_g_lifecycle_recovery_preserves_successful_progress():
    runtime = _runtime()
    assert hasattr(runtime, "RecoveryState")
    assert hasattr(runtime, "recover_preserving_success")
