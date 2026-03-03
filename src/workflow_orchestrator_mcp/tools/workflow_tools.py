"""
MCP Tools for workflow orchestration

Provides the core functions exposed as MCP tools:
- load_workflow: Load and parse a workflow markdown file
- execute_workflow_step: Return enriched prompt for current step
- report_step_result: Callback for LLM to report step outcomes
- get_workflow_state: Get current workflow state
- reset_workflow: Reset workflow to beginning
- get_workflow_template: Return format spec, skeleton, and example
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from actionable_errors import ErrorType

if TYPE_CHECKING:
    from pathlib import Path

from ..common import AssertionResult, StepOutcome, StepStatus
from ..common.errors import WorkflowError
from ..common.prompt_builder import build_enriched_prompt
from ..common.workflow_parser import parse_workflow_markdown
from ..common.workflow_state import get_state, require_loaded_workflow


def load_workflow(file_path: str) -> dict[str, Any]:
    """
    Load and parse a workflow markdown file.

    Args:
        file_path: Path to the workflow markdown file

    Returns:
        Dictionary with success status, step count, and first step info

    Raises:
        ActionableError: If file not found, invalid format, or no steps
    """
    steps = parse_workflow_markdown(file_path)

    state = get_state()
    state.file_path = file_path
    state.steps = steps
    state.current_step = 0
    state.variables.clear()
    state.step_outcomes.clear()

    first_step = steps[0]
    return {
        "success": True,
        "step_count": len(steps),
        "first_step": {
            "name": first_step.name,
            "description": first_step.description,
            "tool_names": first_step.tool_names,
        },
    }


def execute_workflow_step() -> dict[str, Any]:
    """
    Build and return the enriched prompt for the current workflow step.

    The prompt includes the step description, tool names, resolved variables,
    assertion criteria, and instructions to call report_step_result.

    Returns:
        Dictionary with enriched prompt text and step metadata

    Raises:
        WorkflowError: If no workflow loaded or workflow is complete/failed
    """
    state = require_loaded_workflow()

    if state.is_complete:
        raise WorkflowError(
            error="Workflow is already complete",
            error_type=ErrorType.INTERNAL,
            service="workflow-orchestrator",
            suggestion="Use reset_workflow() to run again",
        )
    if state.is_failed:
        raise WorkflowError(
            error="Workflow has failed — cannot continue",
            error_type=ErrorType.INTERNAL,
            service="workflow-orchestrator",
            suggestion="Use reset_workflow() to restart, or fix the issue and resume",
        )

    step = state.get_current_step()
    if step is None:
        raise WorkflowError(
            error="No more steps to execute",
            error_type=ErrorType.INTERNAL,
            service="workflow-orchestrator",
            suggestion="The workflow may be complete — check get_workflow_state()",
        )

    prompt = build_enriched_prompt(step, state.variables)

    return {
        "prompt": prompt,
        "step_number": step.step_number,
        "step_name": step.name,
        "total_steps": state.total_steps,
    }


def report_step_result(
    step_number: int,
    status: str,
    assertion_results: list[dict[str, Any]] | None = None,
    output_variables: dict[str, Any] | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    """
    Callback tool: LLM reports execution results back to orchestrator.

    Updates workflow state with pass/fail per step and extracted variables.
    Returns the next step's enriched prompt or completion status.

    Args:
        step_number: The step number being reported on
        status: "passed" or "failed"
        assertion_results: Per-assertion pass/fail results
        output_variables: Extracted output variable values
        error_message: Error details if the step failed

    Returns:
        Dictionary with next step info or workflow completion status

    Raises:
        WorkflowError: If step is out of order or no workflow loaded
    """
    state = require_loaded_workflow()

    # Validate step ordering
    if step_number != state.current_step:
        raise WorkflowError.step_out_of_order(step_number, state.current_step)

    current_step = state.get_current_step()
    step_status = StepStatus.PASSED if status == "passed" else StepStatus.FAILED

    # Build assertion result objects
    parsed_assertions: list[AssertionResult] = []
    if assertion_results:
        for ar in assertion_results:
            parsed_assertions.append(
                AssertionResult(
                    assertion=ar.get("assertion", ""),
                    passed=ar.get("passed", False),
                    detail=ar.get("detail", ""),
                )
            )

    # Check assertion count mismatch
    expected_count = len(current_step.assertions) if current_step else 0
    actual_count = len(parsed_assertions)
    mismatch_warning = ""
    if expected_count > 0 and actual_count < expected_count:
        mismatch_warning = (
            f"Assertion count mismatch: expected {expected_count}, "
            f"received {actual_count}. {expected_count - actual_count} "
            f"assertion(s) unverified."
        )

    # Record the outcome
    outcome = StepOutcome(
        step_number=step_number,
        status=step_status,
        assertion_results=parsed_assertions,
        output_variables=output_variables or {},
        error_message=error_message,
    )
    state.record_step_outcome(outcome)

    # Advance to next step on success
    if step_status == StepStatus.PASSED:
        state.current_step += 1

        # Build response
        result: dict[str, Any] = {"success": True, "step_number": step_number}
        if mismatch_warning:
            result["warning"] = mismatch_warning

        # If there are more steps, include the next prompt
        next_step = state.get_current_step()
        if next_step:
            next_prompt = build_enriched_prompt(next_step, state.variables)
            result["prompt"] = next_prompt
            result["next_step"] = next_step.step_number
        else:
            result["workflow_complete"] = True

        return result
    else:
        # Failed — return failure summary
        return {
            "success": False,
            "step_number": step_number,
            "status": "failed",
            "error_message": error_message,
            "warning": mismatch_warning if mismatch_warning else None,
        }


def get_workflow_state() -> dict[str, Any]:
    """
    Get the current state of the workflow.

    Returns:
        Dictionary with workflow state information

    Raises:
        WorkflowError: If no workflow has been loaded
    """
    state = require_loaded_workflow()
    return state.to_dict()


def reset_workflow() -> dict[str, Any]:
    """
    Reset the workflow to the beginning.

    Returns:
        Dictionary with reset confirmation

    Raises:
        WorkflowError: If no workflow has been loaded
    """
    state = require_loaded_workflow()
    state.reset()

    return {
        "success": True,
        "current_step": state.current_step,
        "total_steps": state.total_steps,
    }


def get_workflow_template(
    template_path: Path,
    task_description: str | None = None,
) -> dict[str, Any]:
    """
    Return the workflow-format specification, a starter skeleton, and a
    concrete example so the agent can author a new workflow.

    The template content is read from a resource file on disk
    (``docs/workflow_template.md``).

    Args:
        template_path: Absolute path to the template markdown file.
        task_description: Optional brief description of what the workflow
            should accomplish. Included in the response when provided.

    Returns:
        Dictionary with the template text and optional task context.

    Raises:
        WorkflowError: If the template file cannot be found.
    """
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise WorkflowError(
            error=f"Workflow template file not found: {template_path}",
            error_type=ErrorType.NOT_FOUND,
            service="workflow-orchestrator",
            suggestion=(
                "The docs/workflow_template.md file is missing. "
                "Re-install the package or restore the file from the repository."
            ),
        ) from None

    result: dict[str, Any] = {
        "success": True,
        "template": template_text,
    }

    if task_description:
        result["task_description"] = task_description
        result["guidance"] = (
            f"The user wants a workflow that: {task_description}. "
            "Use the template above to create a complete workflow markdown file."
        )

    return result
