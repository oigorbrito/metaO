from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


class DurableStatus(StrEnum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    TERMINATED = "TERMINATED"


@dataclass(frozen=True, slots=True)
class DurableExecutionSpec:
    workflow_name: str
    task_type: str
    input: Mapping[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    timeout_seconds: int = 60
    response_timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.workflow_name or not self.task_type:
            raise ValueError("durable spec requires workflow_name and task_type")
        if min(self.retry_count, self.timeout_seconds, self.response_timeout_seconds) < 0:
            raise ValueError("durable retry/timeout values must be non-negative")
        object.__setattr__(self, "input", MappingProxyType(dict(self.input)))


@dataclass(frozen=True, slots=True)
class DurableExecutionState:
    execution_id: str
    status: DurableStatus
    output: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "output", MappingProxyType(dict(self.output)))


@runtime_checkable
class DurableExecutionPort(Protocol):
    def start(self, spec: DurableExecutionSpec) -> str: ...
    def state(self, execution_id: str) -> DurableExecutionState: ...
    def pause(self, execution_id: str) -> None: ...
    def resume(self, execution_id: str) -> None: ...
    def cancel(self, execution_id: str) -> None: ...
