"""
Error handling utilities for workflow-orchestrator-mcp

Provides ActionableError with AI-friendly guidance for workflow errors.
Extended from demo-assistant-mcp with workflow-specific error types.
"""

from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    """Error types specific to workflow operations"""
    FILE_NOT_FOUND = "file_not_found"
    INVALID_FORMAT = "invalid_format"
    NO_WORKFLOW_LOADED = "no_workflow_loaded"
    EMPTY_WORKFLOW = "empty_workflow"
    MISSING_TOOL_SPEC = "missing_tool_spec"
    VARIABLE_MISSING = "variable_missing"
    STEP_OUT_OF_ORDER = "step_out_of_order"
    ASSERTION_MISMATCH = "assertion_mismatch"
    UNEXPECTED = "unexpected"


class ActionableError(Exception):
    """
    An error that includes a specific suggestion for how to resolve it.

    Used throughout the workflow orchestrator to provide clear guidance to
    the LLM and users when something goes wrong.

    Attributes:
        message: Human-readable error description
        suggestion: Quick action to resolve the error
        error_type: Categorized error type
        example: Optional example of correct format/usage
    """

    def __init__(
        self,
        message: str,
        suggestion: str = "",
        error_type: ErrorType = ErrorType.UNEXPECTED,
        example: Optional[str] = None
    ):
        self.message = message
        self.suggestion = suggestion
        self.error_type = error_type
        self.example = example
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with suggestion and example if provided"""
        parts = [self.message]

        if self.suggestion:
            parts.append(f"\nSuggestion: {self.suggestion}")

        if self.example:
            parts.append(f"\nExample:\n{self.example}")

        return "".join(parts)

    def __str__(self) -> str:
        return self._format_message()

    # Factory methods for common workflow errors

    @classmethod
    def file_not_found(cls, file_path: str) -> "ActionableError":
        """Create a file not found error"""
        return cls(
            message=f"Workflow file not found at {file_path}",
            suggestion="Check that the file path is correct and the file exists",
            error_type=ErrorType.FILE_NOT_FOUND
        )

    @classmethod
    def invalid_format(cls, file_path: str, issue: str) -> "ActionableError":
        """Create an invalid format error with example"""
        return cls(
            message=f"Invalid workflow format in {file_path}: {issue}",
            suggestion="Ensure each step follows the required format",
            error_type=ErrorType.INVALID_FORMAT,
            example=(
                "### 🔧 WORKFLOW STEP: Step name\n"
                "```\n"
                "Step description here\n"
                "```\n"
                "\n"
                "### 🛠️ TOOL: tool_name"
            )
        )

    @classmethod
    def empty_workflow(cls, file_path: str) -> "ActionableError":
        """Create an empty workflow error"""
        return cls(
            message=f"No workflow steps found in {file_path}",
            suggestion="Workflow files must contain at least one step block",
            error_type=ErrorType.EMPTY_WORKFLOW,
            example=(
                "### 🔧 WORKFLOW STEP: Step name\n"
                "```\n"
                "Step description here\n"
                "```\n"
                "\n"
                "### 🛠️ TOOL: tool_name"
            )
        )

    @classmethod
    def no_workflow_loaded(cls, operation: str) -> "ActionableError":
        """Create a no workflow loaded error"""
        return cls(
            message=f"Cannot {operation}: No workflow has been loaded",
            suggestion="Load a workflow first using load_workflow(file_path)",
            error_type=ErrorType.NO_WORKFLOW_LOADED
        )

    @classmethod
    def missing_tool_spec(cls, step_name: str) -> "ActionableError":
        """Create a missing tool specification error"""
        return cls(
            message=f"Step '{step_name}' has no tool specification",
            suggestion="Each workflow step must specify a TOOL or TOOLS section",
            error_type=ErrorType.MISSING_TOOL_SPEC,
            example=(
                "### 🛠️ TOOL: tool_name\n"
                "*or*\n"
                "### 🛠️ TOOLS:\n"
                "- first_tool\n"
                "- second_tool"
            )
        )

    @classmethod
    def variable_missing(cls, variable_name: str, step_name: str) -> "ActionableError":
        """Create a missing variable error"""
        return cls(
            message=f"Variable '{variable_name}' required by step '{step_name}' has not been set",
            suggestion="Ensure a prior step defines this variable in its OUTPUTS section",
            error_type=ErrorType.VARIABLE_MISSING
        )

    @classmethod
    def step_out_of_order(cls, reported_step: int, expected_step: int) -> "ActionableError":
        """Create a step out of order error"""
        return cls(
            message=f"Received result for step {reported_step}, but step {expected_step} is in progress",
            suggestion=f"Report results for step {expected_step} first",
            error_type=ErrorType.STEP_OUT_OF_ORDER
        )
