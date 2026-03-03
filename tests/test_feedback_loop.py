"""
Scenario Group 5: Feedback Loop (report_step_result)

Tests the report_step_result() callback tool — the central innovation
of the workflow orchestrator over the demo-assistant.
"""

from __future__ import annotations

from typing import Any

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
from workflow_orchestrator_mcp.common.workflow_state import StepStatus, WorkflowState, get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def in_progress_workflow(mock_file_system: tuple[Any, Any]) -> WorkflowState:
    """Load workflow and begin first step"""
    load_workflow("/path/to/workflow.md")
    execute_workflow_step()  # starts step 0
    return get_state()


class TestLLMReportsSuccessfulStepOutcome:
    """
    REQUIREMENT: The orchestrator records step success and advances the workflow.

    WHO: The workflow orchestrator processing LLM step reports
    WHAT: A step reported as passed is recorded with PASSED status;
          the response includes the next step's enriched prompt
    WHY: Accurate progress tracking is required so the LLM can continue
         the workflow without extra round-trips

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, get_state, StepStatus
        Never: Construct StepOutcome directly — always obtain via report_step_result
    """

    def test_step_recorded_as_passed(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as passed with all assertions passing
        Then the step outcome status is recorded as PASSED
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports success with passing assertions
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: step 0 is recorded as PASSED
        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.PASSED, (
            f"Expected step 0 status to be PASSED, got {state.step_outcomes[0].status}"
        )

    def test_returns_next_step_prompt(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as passed
        Then the result includes the next step's enriched prompt
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports success
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "my-repo"},
        )

        # Then: the result contains a prompt or next_step key for the next step
        assert "prompt" in result or "next_step" in result, (
            f"Expected 'prompt' or 'next_step' in result keys, got {list(result.keys())}"
        )


class TestLLMReportsFailedStepOutcome:
    """
    REQUIREMENT: The orchestrator records step failure and halts the workflow.

    WHO: The workflow orchestrator processing LLM failure reports
    WHAT: A step reported as failed is recorded with FAILED status;
          the workflow is marked as failed; the result includes a
          failure summary
    WHY: Failed steps must halt the workflow so the LLM can explain
         the issue and remaining steps are not attempted

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, get_state, StepStatus
        Never: Construct StepOutcome directly — always obtain via report_step_result
    """

    def test_step_marked_failed(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as failed with an error message
        Then the step outcome status is recorded as FAILED
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports failure
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        # Then: step 0 is recorded as FAILED
        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.FAILED, (
            f"Expected step 0 status to be FAILED, got {state.step_outcomes[0].status}"
        )

    def test_subsequent_steps_skipped(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as failed
        Then the workflow is marked as failed
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports failure
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        # Then: the workflow is marked as failed
        state = get_state()
        assert state.is_failed is True, (
            f"Expected workflow is_failed to be True, got {state.is_failed}"
        )

    def test_returns_failure_summary(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as failed
        Then the result includes a failure summary
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports failure
        result = report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        # Then: the result indicates failure
        assert result.get("success") is False or "failed" in str(result).lower(), (
            f"Expected failure indicator in result, got {result}"
        )


class TestLLMReportsPartialAssertionResults:
    """
    REQUIREMENT: The orchestrator flags partial assertion results.

    WHO: The workflow orchestrator validating assertion completeness
    WHAT: When the LLM reports fewer assertions than expected, a warning
          about the mismatch is included in the result
    WHY: Unverified assertions must be visible in the report so that
         incomplete validation does not silently pass

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, get_state
        Never: Construct StepOutcome directly — always obtain via report_step_result
    """

    def test_mismatch_flagged(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a step with 2 expected assertions
        When the LLM reports only 1 assertion result
        Then the result contains a warning about the mismatch
        """
        # Given: step 0 has 2 assertions but only 1 will be reported

        # When: the LLM reports with fewer assertions than expected
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: the result contains a warning about the assertion mismatch
        result_str = str(result).lower()
        assert "mismatch" in result_str or "warning" in result_str or "unverified" in result_str, (
            f"Expected 'mismatch', 'warning', or 'unverified' in result, got {result}"
        )


class TestOutputVariablesMergedOnSuccess:
    """
    REQUIREMENT: Output variables are merged into state only on step success.

    WHO: The workflow orchestrator managing variable state across steps
    WHAT: Output variables are available in state after a passed step;
          output variables are NOT merged when a step fails
    WHY: The next step's prompt depends on resolved variable values, and
         failed-step outputs must not pollute the variable namespace

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, get_state
        Never: Mutate state.variables directly — always go through report_step_result
    """

    def test_variables_available_after_success(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as passed with output variables
        Then the output variables are merged into the workflow state
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports success with output variables
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "merged-repo"},
        )

        # Then: REPO_NAME is available in the workflow state
        state = get_state()
        assert state.variables["REPO_NAME"] == "merged-repo", (
            f"Expected REPO_NAME='merged-repo' in state variables, "
            f"got {state.variables.get('REPO_NAME', '<missing>')}"
        )

    def test_variables_not_merged_on_failure(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports step 0 as failed with output variables
        Then the output variables are NOT merged into the workflow state
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports failure with output variables
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {
                    "assertion": 'result contains "repositories"',
                    "passed": False,
                    "detail": "Not found",
                },
            ],
            output_variables={"REPO_NAME": "should-not-persist"},
            error_message="Assertion failed",
        )

        # Then: REPO_NAME is not present in the workflow state
        state = get_state()
        assert "REPO_NAME" not in state.variables, (
            f"Expected REPO_NAME to not be in state variables after failure, "
            f"but found REPO_NAME='{state.variables.get('REPO_NAME')}'"
        )


class TestReportStepResultOutOfOrder:
    """
    REQUIREMENT: The orchestrator rejects out-of-order step reports.

    WHO: The workflow orchestrator enforcing step sequencing
    WHAT: Reporting a result for a step other than the current in-progress
          step raises a WorkflowError with a descriptive message
    WHY: Step results must match the correct step to prevent state
         corruption and ensure deterministic workflow execution

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, WorkflowError
        Never: Construct StepOutcome directly — always obtain via report_step_result
    """

    def test_raises_error_for_wrong_step(self, in_progress_workflow: WorkflowState) -> None:
        """
        Given a workflow with step 0 in progress
        When the LLM reports a result for step 2
        Then a WorkflowError is raised with a descriptive message
        """
        # Given: step 0 is in progress (via in_progress_workflow fixture)

        # When: the LLM reports for step 2 instead of step 0
        with pytest.raises(WorkflowError) as exc_info:
            report_step_result(
                step_number=2,
                status="passed",
                assertion_results=[],
            )

        # Then: the error message references step ordering
        error_msg = str(exc_info.value).lower()
        assert "order" in error_msg or "expected" in error_msg or "step" in error_msg, (
            f"Expected error message to mention 'order', 'expected', or 'step', "
            f"got: {exc_info.value}"
        )
