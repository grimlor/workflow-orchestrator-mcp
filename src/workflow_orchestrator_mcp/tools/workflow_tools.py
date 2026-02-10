"""
MCP Tools for workflow orchestration

Provides the core functions exposed as MCP tools:
- load_workflow: Load and parse a workflow markdown file
- execute_workflow_step: Return enriched prompt for current step
- report_step_result: Callback for LLM to report step outcomes
- get_workflow_state: Get current workflow state
- reset_workflow: Reset workflow to beginning
"""

from typing import Any, Dict, List, Optional

from ..common import ActionableError, AssertionResult, StepOutcome, StepStatus
from ..common.prompt_builder import build_enriched_prompt
from ..common.workflow_parser import parse_workflow_markdown
from ..common.workflow_state import get_state, require_loaded_workflow


def load_workflow(file_path: str) -> Dict[str, Any]:
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


def execute_workflow_step() -> Dict[str, Any]:
    """
    Build and return the enriched prompt for the current workflow step.

    The prompt includes the step description, tool names, resolved variables,
    assertion criteria, and instructions to call report_step_result.

    Returns:
        Dictionary with enriched prompt text and step metadata

    Raises:
        ActionableError: If no workflow loaded or workflow is complete/failed
    """
    state = require_loaded_workflow()

    if state.is_complete:
        raise ActionableError(
            "Workflow is already complete",
            suggestion="Use reset_workflow() to run again",
        )
    if state.is_failed:
        raise ActionableError(
            "Workflow has failed — cannot continue",
            suggestion="Use reset_workflow() to restart, or fix the issue and resume",
        )

    step = state.get_current_step()
    if step is None:
        raise ActionableError(
            "No more steps to execute",
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
    assertion_results: Optional[List[Dict[str, Any]]] = None,
    output_variables: Optional[Dict[str, Any]] = None,
    error_message: str = "",
) -> Dict[str, Any]:
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
        ActionableError: If step is out of order or no workflow loaded
    """
    state = require_loaded_workflow()

    # Validate step ordering
    if step_number != state.current_step:
        raise ActionableError.step_out_of_order(step_number, state.current_step)

    current_step = state.get_current_step()
    step_status = StepStatus.PASSED if status == "passed" else StepStatus.FAILED

    # Build assertion result objects
    parsed_assertions: List[AssertionResult] = []
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
        result: Dict[str, Any] = {"success": True, "step_number": step_number}
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


def get_workflow_state() -> Dict[str, Any]:
    """
    Get the current state of the workflow.

    Returns:
        Dictionary with workflow state information

    Raises:
        ActionableError: If no workflow has been loaded
    """
    state = require_loaded_workflow()
    return state.to_dict()


def reset_workflow() -> Dict[str, Any]:
    """
    Reset the workflow to the beginning.

    Returns:
        Dictionary with reset confirmation

    Raises:
        ActionableError: If no workflow has been loaded
    """
    state = require_loaded_workflow()
    state.reset()

    return {
        "success": True,
        "current_step": state.current_step,
        "total_steps": state.total_steps,
    }
