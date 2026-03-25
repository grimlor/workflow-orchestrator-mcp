"""
Result validation tests.

Covers:
- TestAssertionsEmbeddedInPrompt — assertions appear in enriched prompts
- TestLLMReportsAssertionResults — assertion results recorded and step marked passed
- TestStepMarkedFailedOnAssertionFailure — step marked failed on assertion failure
- TestAssertionCountMismatch — mismatch detection when fewer results reported
"""

from __future__ import annotations

from typing import Any

import pytest

from workflow_orchestrator_mcp.common.workflow_state import (
    StepStatus,
    WorkflowState,
    get_state,
)
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def in_progress_step(mock_file_system: tuple[Any, Any]) -> WorkflowState:
    """Load workflow and start first step so report_step_result can be called"""
    load_workflow("/path/to/workflow.md")
    execute_workflow_step()  # marks step 0 as in-progress
    return get_state()


class TestAssertionsEmbeddedInPrompt:
    """
    REQUIREMENT: Each step's assertions are embedded in the enriched prompt.

    WHO: The orchestrator building prompts for the LLM
    WHAT: The enriched prompt includes every assertion defined for the step
          so the LLM knows exactly what to evaluate
    WHY: Without embedded assertions the LLM cannot verify step outcomes,
         making the workflow validation loop impossible

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  load_workflow, execute_workflow_step, prompt construction
        Never: Construct prompt strings directly — always obtain via execute_workflow_step
    """

    def test_enriched_prompt_contains_each_assertion(
        self, mock_file_system: tuple[Any, Any]
    ) -> None:
        """
        Given a workflow with a step containing two assertions
        When the step is executed and the prompt is built
        Then the prompt contains both assertion strings
        """
        # Given: a loaded workflow whose first step defines two assertions
        load_workflow("/path/to/workflow.md")

        # When: the step is executed and the enriched prompt is produced
        result = execute_workflow_step()
        prompt = result["prompt"]

        # Then: both assertions appear in the prompt text
        assert 'result contains "repositories"' in prompt, (
            f"Expected 'result contains \"repositories\"' in prompt, got: {prompt[:200]}"
        )
        assert "result.repositories.length > 0" in prompt, (
            f"Expected 'result.repositories.length > 0' in prompt, got: {prompt[:200]}"
        )


class TestLLMReportsAssertionResults:
    """
    REQUIREMENT: LLM assertion results are recorded in workflow state.

    WHO: The orchestrator tracking step verification outcomes
    WHAT: All assertion results from report_step_result are stored in state;
          step is marked passed when every assertion passes
    WHY: Without recorded results the orchestrator cannot determine whether
         a step succeeded or which assertions failed

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O via in_progress_step)
        Real:  report_step_result, get_state, WorkflowState, StepStatus
        Never: Mutate step_outcomes directly — always obtain via report_step_result
    """

    def test_all_assertion_results_recorded(self, in_progress_step: WorkflowState) -> None:
        """
        When the LLM reports two passing assertion results
        Then both results are recorded in the step outcome
        """
        # Given: a step that is in-progress (via fixture)

        # When: the LLM reports two passing assertion results
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {
                    "assertion": 'result contains "repositories"',
                    "passed": True,
                    "detail": "Found repositories key",
                },
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": True,
                    "detail": "3 repositories found",
                },
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: both assertion results are stored and marked passed
        state = get_state()
        outcome = state.step_outcomes[0]
        assert len(outcome.assertion_results) == 2, (
            f"Expected 2 assertion results, got {len(outcome.assertion_results)}"
        )
        assert all(r.passed for r in outcome.assertion_results), (
            f"Expected all assertions to pass, got: "
            f"{[(r.assertion, r.passed) for r in outcome.assertion_results]}"
        )

    def test_step_marked_passed_when_all_pass(self, in_progress_step: WorkflowState) -> None:
        """
        When all assertion results are reported as passing
        Then the step status is set to PASSED
        """
        # Given: a step that is in-progress (via fixture)

        # When: report_step_result is called with all assertions passing
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: the step outcome status is PASSED
        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.PASSED, (
            f"Expected step status PASSED, got {state.step_outcomes[0].status}"
        )


class TestStepMarkedFailedOnAssertionFailure:
    """
    REQUIREMENT: Step is marked failed when any assertion fails.

    WHO: The orchestrator deciding whether a step succeeded
    WHAT: If any assertion in the result set has passed=False the step
          status becomes FAILED; failure detail text is preserved verbatim
    WHY: A partially passing step is a failing step — the workflow must
         stop and the failure detail must be available for diagnosis

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O via in_progress_step)
        Real:  report_step_result, get_state, WorkflowState, StepStatus
        Never: Set StepStatus directly — always obtain via report_step_result
    """

    def test_step_fails_when_one_assertion_fails(self, in_progress_step: WorkflowState) -> None:
        """
        Given one passing and one failing assertion result
        When the step result is reported
        Then the step status is FAILED
        """
        # Given: a step in-progress (via fixture) with mixed assertion results

        # When: report_step_result is called with one failing assertion
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": False,
                    "detail": "Empty array returned",
                },
            ],
        )

        # Then: the step outcome status is FAILED
        state = get_state()
        outcome = state.step_outcomes[0]
        assert outcome.status == StepStatus.FAILED, (
            f"Expected step status FAILED, got {outcome.status}"
        )

    def test_failure_detail_preserved(self, in_progress_step: WorkflowState) -> None:
        """
        Given a failing assertion with detail text
        When the step result is reported
        Then the failure detail is preserved in the assertion result
        """
        # Given: a step in-progress (via fixture)

        # When: report_step_result is called with a failing assertion containing detail
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": False,
                    "detail": "Empty array returned",
                },
            ],
        )

        # Then: the assertion is marked failed and the detail text is preserved
        state = get_state()
        failed_assertion = state.step_outcomes[0].assertion_results[0]
        assert failed_assertion.passed is False, (
            f"Expected assertion to be marked failed, got passed={failed_assertion.passed}"
        )
        assert "Empty array" in failed_assertion.detail, (
            f"Expected 'Empty array' in failure detail, got: {failed_assertion.detail!r}"
        )


class TestAssertionCountMismatch:
    """
    REQUIREMENT: Assertion count mismatches are detected and flagged.

    WHO: The orchestrator validating completeness of LLM responses
    WHAT: When the LLM reports fewer assertion results than the step defines,
          the response flags the mismatch so unverified assertions are not
          silently accepted
    WHY: A missing assertion result means the LLM skipped a verification
         check — silently accepting this would undermine workflow integrity

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O via in_progress_step)
        Real:  report_step_result, get_state, WorkflowState
        Never: Bypass report_step_result to set assertion counts directly
    """

    def test_mismatch_flagged_when_fewer_results(self, in_progress_step: WorkflowState) -> None:
        """
        Given a step that defines two assertions
        When the LLM reports only one assertion result
        Then the response flags a mismatch, warning, or unverified status
        """
        # Given: a step in-progress that defines 2 assertions (via fixture)

        # When: report_step_result is called with only 1 assertion result
        result = report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: the result text flags the mismatch
        result_text = str(result).lower()
        assert (
            "mismatch" in result_text or "warning" in result_text or "unverified" in result_text
        ), f"Expected 'mismatch', 'warning', or 'unverified' in result, got: {result_text[:300]}"
