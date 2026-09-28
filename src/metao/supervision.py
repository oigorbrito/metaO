"""Framework-neutral supervision transitions for runtime capacity observations."""

from __future__ import annotations

from dataclasses import replace

from .capacity import CapacityObservation
from .strategy import OrchestratorPoolState


def apply_capacity_observation(
    pools: tuple[OrchestratorPoolState, ...],
    *,
    orchestrator_id: str,
    observation: CapacityObservation | None,
) -> tuple[OrchestratorPoolState, ...]:
    """Return an immutable pool snapshot updated by one capacity observation.

    The transition is explicit: callers decide when the returned snapshot becomes
    authoritative for a later selection cycle. Health, budget and acceptance are
    intentionally untouched.
    """
    if observation is None:
        return pools

    updated: list[OrchestratorPoolState] = []
    matched = False
    for pool in pools:
        if pool.orchestrator_id != orchestrator_id:
            updated.append(pool)
            continue
        matched = True
        recovery = observation.recovery
        updated.append(
            replace(
                pool,
                capacity_status=observation.capacity_status,
                recover_at_epoch=(recovery.recover_at_epoch if recovery is not None else None),
                recovery=recovery,
            )
        )

    if not matched:
        raise KeyError(f"capacity observation references unknown orchestrator: {orchestrator_id}")
    return tuple(updated)


__all__ = ["apply_capacity_observation"]
