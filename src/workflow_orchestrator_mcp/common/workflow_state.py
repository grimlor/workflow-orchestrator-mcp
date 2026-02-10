"""
Workflow state management

Tracks the current position in a workflow, step outcomes (passed/failed/skipped),
runtime variables, and assertion results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StepStatus(str, Enum):
    """Status of an individual workflow step"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AssertionResult:
    """LLM-reported result for a single assertion"""
    assertion: str
    passed: bool
    detail: str = ""


@dataclass
class StepOutcome:
    """Reported by LLM via report_step_result callback"""
    step_number: int
    status: StepStatus
    assertion_results: List[AssertionResult] = field(default_factory=list)
    output_variables: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""

    @property
    def all_assertions_passed(self) -> bool:
        return all(r.passed for r in self.assertion_results)


@dataclass
class WorkflowStep:
    """Represents a single step extracted from a workflow script"""
    step_number: int
    name: str
    description: str
    tool_names: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    assertions: List[str] = field(default_factory=list)
    section_title: str = ""


@dataclass
class WorkflowState:
    """
    Manages the state of a workflow execution session.

    Tracks which workflow is loaded, current position, step outcomes,
    and runtime variables. Follows singleton pattern (one workflow at a time).
    Concurrent workflow execution would require scoped state keyed by workflow ID.
    """

    file_path: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    current_step: int = 0  # Index in steps list (0-based)
    variables: Dict[str, Any] = field(default_factory=dict)
    step_outcomes: Dict[int, StepOutcome] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> List[int]:
        return [n for n, o in self.step_outcomes.items() if o.status == StepStatus.PASSED]

    @property
    def failed_steps(self) -> List[int]:
        return [n for n, o in self.step_outcomes.items() if o.status == StepStatus.FAILED]

    @property
    def is_failed(self) -> bool:
        return any(o.status == StepStatus.FAILED for o in self.step_outcomes.values())

    @property
    def is_complete(self) -> bool:
        return len(self.step_outcomes) >= self.total_steps

    @property
    def is_loaded(self) -> bool:
        return bool(self.file_path and self.steps)

    def record_step_outcome(self, outcome: StepOutcome) -> None:
        """Record LLM-reported outcome and merge output variables"""
        self.step_outcomes[outcome.step_number] = outcome
        if outcome.status == StepStatus.PASSED:
            self.variables.update(outcome.output_variables)

    def reset(self) -> None:
        """Reset workflow to beginning while keeping steps loaded"""
        self.current_step = 0
        self.variables.clear()
        self.step_outcomes.clear()

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the step at the current position"""
        if 0 <= self.current_step < self.total_steps:
            return self.steps[self.current_step]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "file_path": self.file_path,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "is_complete": self.is_complete,
            "is_failed": self.is_failed,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "variables": self.variables,
            "step_outcomes": {
                n: {
                    "status": o.status.value,
                    "assertion_results": [
                        {"assertion": r.assertion, "passed": r.passed, "detail": r.detail}
                        for r in o.assertion_results
                    ],
                    "output_variables": o.output_variables,
                    "error_message": o.error_message,
                }
                for n, o in self.step_outcomes.items()
            },
        }


# Global state instance (one workflow session at a time)
_workflow_state = WorkflowState()


def get_state() -> WorkflowState:
    """Get the current workflow state"""
    return _workflow_state


def require_loaded_workflow() -> WorkflowState:
    """
    Get the current state and verify a workflow is loaded.

    Returns:
        The current workflow state

    Raises:
        ActionableError: If no workflow has been loaded
    """
    from .error_handling import ActionableError

    state = get_state()
    if not state.is_loaded:
        raise ActionableError.no_workflow_loaded("proceed with operation")
    return state
