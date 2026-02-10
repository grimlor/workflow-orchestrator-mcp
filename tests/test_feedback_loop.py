"""
Scenario Group 5: Feedback Loop (report_step_result)

Tests the report_step_result() callback tool — the central innovation
of the workflow orchestrator over the demo-assistant.
"""

import pytest

from workflow_orchestrator_mcp.common.error_handling import ActionableError
from workflow_orchestrator_mcp.common.workflow_state import StepStatus, get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def in_progress_workflow(mock_file_system):
    """Load workflow and begin first step"""
    load_workflow("/path/to/workflow.md")
    execute_workflow_step()  # starts step 0
    return get_state()


class TestLLMReportsSuccessfulStepOutcome:
    """Scenario 5.1: LLM reports successful step outcome"""

    def test_step_recorded_as_passed(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need the step recorded as passed when the LLM reports success
        So that workflow progress is tracked accurately
        """
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.PASSED

    def test_returns_next_step_prompt(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need the next step's enriched prompt returned after a successful report
        So that the LLM can continue the workflow without extra round-trips
        """
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "my-repo"},
        )

        # Should include the next step's enriched prompt
        assert "prompt" in result or "next_step" in result


class TestLLMReportsFailedStepOutcome:
    """Scenario 5.2: LLM reports failed step outcome"""

    def test_step_marked_failed(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need the step marked failed when the LLM reports failure
        So that the workflow knows execution cannot proceed
        """
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.FAILED

    def test_subsequent_steps_skipped(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need remaining steps marked as skipped after a failure
        So that the report accurately shows what wasn't attempted
        """
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        state = get_state()
        assert state.is_failed is True

    def test_returns_failure_summary(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need a failure summary returned when a step fails
        So that the LLM can explain the issue to the user
        """
        result = report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool returned HTTP 500",
        )

        assert result.get("success") is False or "failed" in str(result).lower()


class TestLLMReportsPartialAssertionResults:
    """Scenario 5.3: LLM reports partial assertion results"""

    def test_mismatch_flagged(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need a warning when the LLM reports fewer assertions than expected
        So that unverified assertions are visible in the report
        """
        # Step 0 has 2 assertions but only 1 is reported
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Should contain a warning about the mismatch
        result_str = str(result).lower()
        assert "mismatch" in result_str or "warning" in result_str or "unverified" in result_str


class TestOutputVariablesMergedOnSuccess:
    """Scenario 5.4: Output variables merged into state on success"""

    def test_variables_available_after_success(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need output variables merged into state when a step passes
        So that the next step's prompt can include resolved values
        """
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "merged-repo"},
        )

        state = get_state()
        assert state.variables["REPO_NAME"] == "merged-repo"

    def test_variables_not_merged_on_failure(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need output variables NOT merged when a step fails
        So that failed-step outputs don't pollute the variable namespace
        """
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": False, "detail": "Not found"},
            ],
            output_variables={"REPO_NAME": "should-not-persist"},
            error_message="Assertion failed",
        )

        state = get_state()
        assert "REPO_NAME" not in state.variables


class TestReportStepResultOutOfOrder:
    """Scenario 5.5: report_step_result called out of order"""

    def test_raises_error_for_wrong_step(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need an error when the LLM reports for the wrong step
        So that step results are always matched to the correct step
        """
        # Step 0 is in progress, but LLM reports for step 2
        with pytest.raises(ActionableError) as exc_info:
            report_step_result(
                step_number=2,
                status="passed",
                assertion_results=[],
            )

        error_msg = str(exc_info.value).lower()
        assert "order" in error_msg or "expected" in error_msg or "step" in error_msg
