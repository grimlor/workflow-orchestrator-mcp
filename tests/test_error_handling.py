"""
Error handling and reporting specifications

Tests error handling for parsing failures, workflow execution reports,
and detailed failure diagnostics.

Spec classes:
    TestActionableErrorForParsingFailure
    TestWorkflowExecutionReport
    TestDetailedFailureDiagnostics
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
from workflow_orchestrator_mcp.common.workflow_state import get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
)


class TestActionableErrorForParsingFailure:
    """
    REQUIREMENT: Malformed workflow markdown produces actionable errors.

    WHO: The workflow author writing or editing a workflow file
    WHAT: Malformed markdown raises a WorkflowError with a message that
          describes the formatting issue; missing tools produce an error
          that suggests the correct format
    WHY: Generic or empty error messages force the author to guess what's
         wrong — actionable messages reduce fix time from minutes to seconds

    MOCK BOUNDARY:
        Mock:  filesystem via patch (pathlib.Path.exists, pathlib.Path.read_text)
        Real:  workflow parser, WorkflowError construction
        Never: Construct WorkflowError directly — always trigger via load_workflow
    """

    def test_malformed_markdown_raises_actionable_error(self) -> None:
        """
        Given a markdown file with malformed workflow step syntax
        When the workflow is loaded
        Then a WorkflowError is raised with a message describing the issue
        """
        # Given: malformed markdown with an empty step name
        malformed = """# Broken Workflow
### 🔧 WORKFLOW STEP:
```
Step with empty name
```
"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=malformed),
        ):
            # When: the workflow is loaded
            with pytest.raises(WorkflowError) as exc_info:
                load_workflow("/path/to/malformed.md")

            # Then: the error message describes the parsing issue
            error = str(exc_info.value)
            assert "step" in error.lower() or "workflow" in error.lower(), (
                f"Expected error to describe the parsing issue "
                f"(mention 'step' or 'workflow'), got: {error}"
            )

    def test_error_suggests_correct_format(self, workflow_without_tools: str) -> None:
        """
        Given a workflow markdown file that is missing tool declarations
        When the workflow is loaded
        Then the error message mentions "tool" to guide the author
        """
        # Given: a workflow markdown without tool declarations
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=workflow_without_tools),
        ):
            # When: the workflow is loaded
            with pytest.raises(WorkflowError) as exc_info:
                load_workflow("/path/to/bad.md")

            # Then: the error message mentions "tool"
            error = str(exc_info.value)
            assert "tool" in error.lower(), (
                f"Expected 'tool' in error message to guide the author, got: {error}"
            )


class TestWorkflowExecutionReport:
    """
    REQUIREMENT: The execution report accurately reflects all step outcomes.

    WHO: The workflow author reviewing a completed or failed run
    WHAT: The state dict includes step_outcomes keyed by step index,
          each with correct status and assertion details including
          pass/fail and LLM-provided detail text
    WHY: The report is the author's only post-run diagnostic tool —
         missing or inaccurate outcome data makes debugging impossible

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, report_step_result, get_workflow_state
        Never: Construct step outcomes directly — always via report_step_result
    """

    def test_report_shows_all_step_statuses(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow where step 1 passes and step 2 fails
        When the workflow state is queried
        Then step_outcomes contains both steps with correct statuses
        """
        # Given: a loaded workflow
        load_workflow("/path/to/workflow.md")
        get_state()

        # When: step 1 passes and step 2 fails
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": True,
                    "detail": "3 repos",
                },
            ],
            output_variables={"REPO_NAME": "my-repo"},
        )

        execute_workflow_step()
        report_step_result(
            step_number=1,
            status="failed",
            assertion_results=[
                {"assertion": "result.success == true", "passed": False, "detail": "Got false"},
            ],
            error_message="Context not set",
        )

        state_dict = get_workflow_state()

        # Then: both steps have outcomes with correct statuses
        assert "step_outcomes" in state_dict, (
            f"Expected 'step_outcomes' key in state dict, got keys: {list(state_dict.keys())}"
        )
        assert 0 in state_dict["step_outcomes"], (
            f"Expected step 0 in step_outcomes, got: {list(state_dict['step_outcomes'].keys())}"
        )
        assert 1 in state_dict["step_outcomes"], (
            f"Expected step 1 in step_outcomes, got: {list(state_dict['step_outcomes'].keys())}"
        )
        assert state_dict["step_outcomes"][0]["status"] == "passed", (
            f"Expected step 0 status 'passed', got '{state_dict['step_outcomes'][0]['status']}'"
        )
        assert state_dict["step_outcomes"][1]["status"] == "failed", (
            f"Expected step 1 status 'failed', got '{state_dict['step_outcomes'][1]['status']}'"
        )

    def test_report_shows_assertion_detail(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow step reported with assertion results including detail text
        When the workflow state is queried
        Then each assertion result includes its pass/fail status and detail text
        """
        # Given: a loaded workflow
        load_workflow("/path/to/workflow.md")

        # When: a step is executed and reported with assertion details
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {
                    "assertion": 'result contains "repositories"',
                    "passed": True,
                    "detail": "Found key in response",
                },
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": True,
                    "detail": "3 items",
                },
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        state_dict = get_workflow_state()
        step_0_assertions = state_dict["step_outcomes"][0]["assertion_results"]

        # Then: assertion results contain pass/fail and detail text
        assert len(step_0_assertions) == 2, (
            f"Expected 2 assertion results, got {len(step_0_assertions)}"
        )
        assert step_0_assertions[0]["passed"] is True, (
            f"Expected first assertion passed=True, got {step_0_assertions[0]['passed']}"
        )
        assert "Found key" in step_0_assertions[0]["detail"], (
            f"Expected 'Found key' in detail, got '{step_0_assertions[0]['detail']}'"
        )


class TestDetailedFailureDiagnostics:
    """
    REQUIREMENT: Failed assertions include the assertion text and LLM explanation.

    WHO: The workflow author diagnosing a failed step
    WHAT: The failed assertion entry contains the original assertion text
          and the LLM-provided detail explaining the failure; error messages
          from the LLM are preserved verbatim in the report
    WHY: Without the assertion text and explanation the author cannot
         distinguish between different failure modes in the same step

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, report_step_result, get_workflow_state
        Never: Construct AssertionResult directly — always via report_step_result
    """

    def test_failure_shows_assertion_text_and_detail(
        self, mock_file_system: tuple[Any, Any]
    ) -> None:
        """
        Given a workflow step that failed with one assertion including detail text
        When the workflow state is queried
        Then the failed assertion entry contains the assertion text and detail
        """
        # Given: a loaded workflow
        load_workflow("/path/to/workflow.md")

        # When: a step is reported as failed with assertion detail
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[
                {
                    "assertion": "result.repositories.length > 0",
                    "passed": False,
                    "detail": "API returned empty array: no repositories found for user",
                },
            ],
            error_message="Assertion failed",
        )

        state_dict = get_workflow_state()
        failed_assertions = [
            a for a in state_dict["step_outcomes"][0]["assertion_results"] if not a["passed"]
        ]

        # Then: the failed assertion contains assertion text and detail
        assert len(failed_assertions) == 1, (
            f"Expected 1 failed assertion, got {len(failed_assertions)}"
        )
        assert "result.repositories.length > 0" in failed_assertions[0]["assertion"], (
            f"Expected assertion text in result, got '{failed_assertions[0]['assertion']}'"
        )
        assert "empty array" in failed_assertions[0]["detail"].lower(), (
            f"Expected 'empty array' in detail, got '{failed_assertions[0]['detail']}'"
        )

    def test_error_message_preserved_in_report(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow step that failed with an error message
        When the workflow state is queried
        Then the error message is preserved verbatim in the step outcome
        """
        # Given: a loaded workflow
        load_workflow("/path/to/workflow.md")

        # When: a step is reported as failed with an error message
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[],
            error_message="Connection timeout after 30s",
        )

        # Then: the error message is preserved in the report
        state_dict = get_workflow_state()
        assert state_dict["step_outcomes"][0]["error_message"] == "Connection timeout after 30s", (
            f"Expected error message 'Connection timeout after 30s', "
            f"got '{state_dict['step_outcomes'][0]['error_message']}'"
        )
