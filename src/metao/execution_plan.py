from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Sequence

class PlanStepStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    description: str
    required_capabilities: frozenset[str] = frozenset()
    critical: bool = True  # If False, failure might not halt the whole plan

@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    plan_id: str
    steps: Sequence[PlanStep]
    
    def get_next_step(self, completed_steps: frozenset[str]) -> Optional[PlanStep]:
        for step in self.steps:
            if step.step_id not in completed_steps:
                return step
        return None

@dataclass(frozen=True, slots=True)
class DefaultLinearPlan(ExecutionPlan):
    """
    Implements a simple linear plan based on a max number of attempts.
    Used for backward compatibility with the legacy loop.
    """
    def __init__(self, plan_id: str, max_attempts: int = 3):
        steps = [
            PlanStep(step_id=f"attempt_{i+1}", description=f"Mission attempt {i+1}")
            for i in range(max_attempts)
        ]
        ExecutionPlan.__init__(self, plan_id=plan_id, steps=tuple(steps))

__all__ = ["PlanStepStatus", "PlanStep", "ExecutionPlan", "DefaultLinearPlan"]
