"""
Scenario Group 3: Result Validation

Tests the public API: report_step_result() and its effect on workflow state.
Assertions are embedded in prompts (Group 2) and results reported back here.
"""

import pytest

from workflow_orchestrator_mcp.common.workflow_state import (
    StepStatus,
    get_state,
)
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def in_progress_step(mock_file_system):
    """Load workflow and start first step so report_step_result can be called"""
    load_workflow("/path/to/workflow.md")
    execute_workflow_step()  # marks step 0 as in-progress
    return get_state()


class TestAssertionsEmbeddedInPrompt:
    """Scenario 3.1: Assertions embedded in enriched prompt"""

    def test_enriched_prompt_contains_each_assertion(self, mock_file_system):
        """
        As a workflow orchestrator
        I need each assertion embedded in the prompt
        So that the LLM knows exactly what to evaluate
        """
        load_workflow("/path/to/workflow.md")
        result = execute_workflow_step()

        prompt = result["prompt"]
        # Step 1 has two assertions
        assert 'result contains "repositories"' in prompt
        assert "result.repositories.length > 0" in prompt


class TestLLMReportsAssertionResults:
    """Scenario 3.2: LLM reports assertion results via callback"""

    def test_all_assertion_results_recorded(self, in_progress_step):
        """
        As a workflow orchestrator
        I need the LLM's assertion results recorded in state
        So that I can track which criteria passed or failed
        """
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found repositories key"},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": "3 repositories found"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        state = get_state()
        outcome = state.step_outcomes[0]
        assert len(outcome.assertion_results) == 2
        assert all(r.passed for r in outcome.assertion_results)

    def test_step_marked_passed_when_all_pass(self, in_progress_step):
        """
        As a workflow orchestrator
        I need the step marked passed when all assertions succeed
        So that the workflow can proceed to the next step
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


class TestStepMarkedFailedOnAssertionFailure:
    """Scenario 3.3: Step marked failed when any assertion fails"""

    def test_step_fails_when_one_assertion_fails(self, in_progress_step):
        """
        As a workflow orchestrator
        I need the step marked failed when any assertion fails
        So that the workflow stops and reports the issue
        """
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
                {"assertion": "result.repositories.length > 0", "passed": False, "detail": "Empty array returned"},
            ],
        )

        state = get_state()
        outcome = state.step_outcomes[0]
        assert outcome.status == StepStatus.FAILED

    def test_failure_detail_preserved(self, in_progress_step):
        """
        As a workflow orchestrator
        I need the failure detail from the LLM preserved
        So that the report shows why each assertion failed
        """
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {"assertion": "result.repositories.length > 0", "passed": False, "detail": "Empty array returned"},
            ],
        )

        state = get_state()
        failed_assertion = state.step_outcomes[0].assertion_results[0]
        assert failed_assertion.passed is False
        assert "Empty array" in failed_assertion.detail


class TestAssertionCountMismatch:
    """Scenario 3.4: Assertion count mismatch detection"""

    def test_mismatch_flagged_when_fewer_results(self, in_progress_step):
        """
        As a workflow orchestrator
        I need to detect when the LLM reports fewer assertions than expected
        So that missing assertions are treated as unverified
        """
        # Step 1 has 2 assertions, but LLM only reports 1
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Should flag the mismatch
        result_text = str(result).lower()
        assert "mismatch" in result_text or "warning" in result_text or "unverified" in result_text
