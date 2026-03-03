"""
Domain error types for workflow-orchestrator-mcp

Extends the ``actionable-errors`` library with workflow-specific error
categories and convenience factory methods that preserve the local API
surface while delegating structured error formatting to the library.
"""

from __future__ import annotations

from enum import StrEnum

from actionable_errors import ActionableError, ErrorType

_SERVICE = "workflow-orchestrator"


class WorkflowErrorType(StrEnum):
    """Workflow-specific error categories.

    A standalone ``StrEnum`` whose string values can be passed as the
    ``error_type`` argument to :class:`ActionableError` (which accepts
    ``ErrorType | str``).  Python forbids subclassing an enum that already
    has members, so this is a sibling enum rather than a child of
    :class:`ErrorType`.
    """

    NO_WORKFLOW_LOADED = "no_workflow_loaded"
    EMPTY_WORKFLOW = "empty_workflow"
    MISSING_TOOL_SPEC = "missing_tool_spec"
    VARIABLE_MISSING = "variable_missing"
    STEP_OUT_OF_ORDER = "step_out_of_order"
    ASSERTION_MISMATCH = "assertion_mismatch"


class WorkflowError(ActionableError):
    """Actionable error with workflow-specific factory methods.

    Every factory sets ``service`` to ``"workflow-orchestrator"`` so that
    downstream consumers can identify the source without inspecting the
    error type.
    """

    # ------------------------------------------------------------------
    # Factory classmethods
    # ------------------------------------------------------------------

    @classmethod
    def file_not_found(cls, file_path: str) -> "WorkflowError":
        """Create a file-not-found error."""
        return cls(
            error=f"Workflow file not found at {file_path}",
            error_type=ErrorType.NOT_FOUND,
            service=_SERVICE,
            suggestion="Check that the file path is correct and the file exists",
        )

    @classmethod
    def invalid_format(cls, file_path: str, issue: str) -> "WorkflowError":
        """Create an invalid-format error with an example."""
        return cls(
            error=f"Invalid workflow format in {file_path}: {issue}",
            error_type=ErrorType.VALIDATION,
            service=_SERVICE,
            suggestion="Ensure each step follows the required format",
        )

    @classmethod
    def empty_workflow(cls, file_path: str) -> "WorkflowError":
        """Create an empty-workflow error."""
        return cls(
            error=f"No workflow steps found in {file_path}",
            error_type=WorkflowErrorType.EMPTY_WORKFLOW,
            service=_SERVICE,
            suggestion="Workflow files must contain at least one step block",
        )

    @classmethod
    def no_workflow_loaded(cls, operation: str) -> "WorkflowError":
        """Create a no-workflow-loaded error."""
        return cls(
            error=f"Cannot {operation}: No workflow has been loaded",
            error_type=WorkflowErrorType.NO_WORKFLOW_LOADED,
            service=_SERVICE,
            suggestion="Load a workflow first using load_workflow(file_path)",
        )

    @classmethod
    def missing_tool_spec(cls, step_name: str) -> "WorkflowError":
        """Create a missing-tool-specification error."""
        return cls(
            error=f"Step '{step_name}' has no tool specification",
            error_type=WorkflowErrorType.MISSING_TOOL_SPEC,
            service=_SERVICE,
            suggestion="Each workflow step must specify a TOOL or TOOLS section",
        )

    @classmethod
    def variable_missing(cls, variable_name: str, step_name: str) -> "WorkflowError":
        """Create a missing-variable error."""
        return cls(
            error=(
                f"Variable '{variable_name}' required by step "
                f"'{step_name}' has not been set"
            ),
            error_type=WorkflowErrorType.VARIABLE_MISSING,
            service=_SERVICE,
            suggestion="Ensure a prior step defines this variable in its OUTPUTS section",
        )

    @classmethod
    def step_out_of_order(cls, reported_step: int, expected_step: int) -> "WorkflowError":
        """Create a step-out-of-order error."""
        return cls(
            error=(
                f"Received result for step {reported_step}, "
                f"but step {expected_step} is in progress"
            ),
            error_type=WorkflowErrorType.STEP_OUT_OF_ORDER,
            service=_SERVICE,
            suggestion=f"Report results for step {expected_step} first",
        )
