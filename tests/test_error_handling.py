"""
Scenario Group 7: Error Handling and Reporting

Tests error handling and the final workflow execution report.
"""

from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.error_handling import ActionableError
from workflow_orchestrator_mcp.common.workflow_state import get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
)


class TestActionableErrorForParsingFailure:
    """Scenario 7.1: Actionable error for parsing failure"""

    def test_malformed_markdown_raises_actionable_error(self):
        """
        As a workflow author
        I need clear errors when my markdown is malformed
        So that I can fix the formatting issues
        """
        malformed = """# Broken Workflow
### 🔧 WORKFLOW STEP:
```
Step with empty name
```
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=malformed):
            with pytest.raises(ActionableError) as exc_info:
                load_workflow("/path/to/malformed.md")

            error = str(exc_info.value)
            # Should contain actionable information
            assert len(error) > 0

    def test_error_suggests_correct_format(self, workflow_without_tools):
        """
        As a workflow author
        I need error messages that suggest the correct format
        So that I can fix my workflow quickly
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=workflow_without_tools):
            with pytest.raises(ActionableError) as exc_info:
                load_workflow("/path/to/bad.md")

            error = str(exc_info.value)
            assert "tool" in error.lower()


class TestWorkflowExecutionReport:
    """Scenario 7.2: Workflow execution report"""

    def test_report_shows_all_step_statuses(self, mock_file_system):
        """
        As a workflow author
        I need the execution report to show each step's status
        So that I can see the full picture of what happened
        """
        load_workflow("/path/to/workflow.md")
        get_state()

        # Step 1 passes
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found"},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": "3 repos"},
            ],
            output_variables={"REPO_NAME": "my-repo"},
        )

        # Step 2 fails
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

        # Should have outcomes for both executed steps
        assert "step_outcomes" in state_dict
        assert 0 in state_dict["step_outcomes"]
        assert 1 in state_dict["step_outcomes"]
        assert state_dict["step_outcomes"][0]["status"] == "passed"
        assert state_dict["step_outcomes"][1]["status"] == "failed"

    def test_report_shows_assertion_detail(self, mock_file_system):
        """
        As a workflow author
        I need assertion results with LLM-provided detail per step
        So that I understand exactly what passed and failed
        """
        load_workflow("/path/to/workflow.md")

        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": "Found key in response"},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": "3 items"},
            ],
            output_variables={"REPO_NAME": "test-repo"},
        )

        state_dict = get_workflow_state()
        step_0_assertions = state_dict["step_outcomes"][0]["assertion_results"]

        assert len(step_0_assertions) == 2
        assert step_0_assertions[0]["passed"] is True
        assert "Found key" in step_0_assertions[0]["detail"]


class TestDetailedFailureDiagnostics:
    """Scenario 7.3: Detailed failure diagnostics"""

    def test_failure_shows_assertion_text_and_detail(self, mock_file_system):
        """
        As a workflow author
        I need the failed assertion text and LLM explanation
        So that I can understand and fix the root cause
        """
        load_workflow("/path/to/workflow.md")

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
            a for a in state_dict["step_outcomes"][0]["assertion_results"]
            if not a["passed"]
        ]

        assert len(failed_assertions) == 1
        assert "result.repositories.length > 0" in failed_assertions[0]["assertion"]
        assert "empty array" in failed_assertions[0]["detail"].lower()

    def test_error_message_preserved_in_report(self, mock_file_system):
        """
        As a workflow author
        I need the error message from the LLM preserved in the report
        So that diagnostic context isn't lost
        """
        load_workflow("/path/to/workflow.md")

        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="failed",
            assertion_results=[],
            error_message="Connection timeout after 30s",
        )

        state_dict = get_workflow_state()
        assert state_dict["step_outcomes"][0]["error_message"] == "Connection timeout after 30s"
