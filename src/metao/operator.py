"""Small public operator facade over a configured DurableExecutionPort.

These functions intentionally require the port as an explicit argument. metaO
therefore has no hidden global runtime and remains testable/replaceable.
"""

from __future__ import annotations

from metao.durable import DurableExecutionPort, DurableExecutionSpec, DurableExecutionState


def run(port: DurableExecutionPort, spec: DurableExecutionSpec) -> str:
    return port.start(spec)


def status(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    return port.state(execution_id)


def inspect(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    """Return the current authoritative durable execution state."""
    return port.state(execution_id)


def cancel(port: DurableExecutionPort, execution_id: str) -> None:
    port.cancel(execution_id)


def resume(port: DurableExecutionPort, execution_id: str) -> None:
    port.resume(execution_id)


__all__ = ["run", "status", "inspect", "cancel", "resume"]
