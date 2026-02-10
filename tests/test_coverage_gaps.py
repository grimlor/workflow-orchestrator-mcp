"""
Coverage gap specifications

Tests for behaviors that weren't covered by the original 7 scenario groups.
Each test specifies a behavioral contract for an edge case or alternate path.
"""

from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.error_handling import ActionableError
from workflow_orchestrator_mcp.common.workflow_state import (
    AssertionResult,
    StepOutcome,
    StepStatus,
    get_state,
    require_loaded_workflow,
)
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
    reset_workflow,
)


class TestNoWorkflowLoadedGuard:
    """Behaviors when operating on state before any workflow is loaded"""

    def test_get_workflow_state_raises_when_nothing_loaded(self):
        """
        As a workflow user
        I need a clear error when querying state before loading
        So that I know to load a workflow first
        """
        with pytest.raises(ActionableError) as exc_info:
            get_workflow_state()

        assert "no workflow has been loaded" in str(exc_info.value).lower()

    def test_reset_workflow_raises_when_nothing_loaded(self):
        """
        As a workflow user
        I need a clear error when resetting before loading
        So that I know there's nothing to reset
        """
        with pytest.raises(ActionableError) as exc_info:
            reset_workflow()

        assert "no workflow has been loaded" in str(exc_info.value).lower()

    def test_require_loaded_workflow_raises_actionable_error(self):
        """
        As a workflow orchestrator
        I need the guard function to raise with load instructions
        So that any tool can delegate the check
        """
        with pytest.raises(ActionableError) as exc_info:
            require_loaded_workflow()

        assert "load_workflow" in str(exc_info.value).lower()


class TestExecuteWorkflowStepGuards:
    """Edge cases for execute_workflow_step when workflow is in terminal state"""

    def test_raises_when_workflow_is_complete(self, mock_file_system):
        """
        As a workflow user
        I need an error when all steps are already done
        So that I know to reset if I want to run again
        """
        load_workflow("/path/to/workflow.md")
        state = get_state()

        # Run through all 3 steps
        for i in range(3):
            execute_workflow_step()
            outputs = {"REPO_NAME": "r"} if i == 0 else ({"PR_ID": "1"} if i == 2 else {})
            report_step_result(
                step_number=i,
                status="passed",
                assertion_results=[
                    {"assertion": a, "passed": True, "detail": "ok"}
                    for a in state.steps[i].assertions
                ],
                output_variables=outputs,
            )

        assert state.is_complete

        with pytest.raises(ActionableError) as exc_info:
            execute_workflow_step()

        assert "complete" in str(exc_info.value).lower()

    def test_raises_when_workflow_has_failed(self, mock_file_system):
        """
        As a workflow user
        I need an error when the workflow has already failed
        So that I know to reset or fix the issue
        """
        load_workflow("/path/to/workflow.md")

        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool not available",
        )

        state = get_state()
        assert state.is_failed

        with pytest.raises(ActionableError) as exc_info:
            execute_workflow_step()

        assert "failed" in str(exc_info.value).lower()


class TestStepOutcomeAllAssertionsPassed:
    """Specification for StepOutcome.all_assertions_passed property"""

    def test_true_when_all_pass(self):
        """
        As a workflow orchestrator
        I need to know when all assertions in an outcome passed
        So that I can make pass/fail decisions
        """
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.PASSED,
            assertion_results=[
                AssertionResult(assertion="a > 0", passed=True),
                AssertionResult(assertion="b > 0", passed=True),
            ],
        )
        assert outcome.all_assertions_passed is True

    def test_false_when_any_fails(self):
        """
        As a workflow orchestrator
        I need to detect when any assertion failed
        So that the step can be marked accordingly
        """
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.FAILED,
            assertion_results=[
                AssertionResult(assertion="a > 0", passed=True),
                AssertionResult(assertion="b > 0", passed=False, detail="was 0"),
            ],
        )
        assert outcome.all_assertions_passed is False

    def test_true_when_no_assertions(self):
        """
        As a workflow orchestrator
        I need steps without assertions to vacuously pass
        So that assertion-free steps aren't incorrectly flagged
        """
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.PASSED,
            assertion_results=[],
        )
        assert outcome.all_assertions_passed is True


class TestParserEdgeCases:
    """Parsing edge cases not covered by Group 1 scenarios"""

    def test_file_read_error_raises_actionable_error(self):
        """
        As a workflow author
        I need a clear error when the file can't be read (permissions, encoding)
        So that I can fix the access issue
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
            with pytest.raises(ActionableError) as exc_info:
                load_workflow("/path/to/unreadable.md")

            assert "failed to read" in str(exc_info.value).lower()

    def test_ascii_arrow_in_outputs(self):
        """
        As a workflow author
        I need -> (ASCII arrow) to work in OUTPUTS alongside →
        So that I can write workflows without special characters
        """
        workflow_with_ascii_arrow = """# ASCII Arrow Workflow

### 🔧 WORKFLOW STEP: Extract data
```
Run extraction tool
```

### 🛠️ TOOL: extract_tool

### 📤 OUTPUTS:
- result.id -> ENTITY_ID

### ✅ ASSERT:
- result.id exists
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=workflow_with_ascii_arrow):
            load_workflow("/path/to/ascii.md")

        state = get_state()
        step = state.steps[0]
        assert "ENTITY_ID" in step.outputs.values()
        assert "result.id" in step.outputs.keys()


class TestExecuteWorkflowStepDefensiveGuard:
    """Defensive behavior when get_current_step returns None unexpectedly"""

    def test_step_none_after_guards_pass_raises_actionable_error(self, mock_file_system):
        """
        As a workflow orchestrator
        I need a safety net if get_current_step() returns None despite guards passing
        So that the user gets a helpful error instead of a crash
        """
        load_workflow("/path/to/workflow.md")
        state = get_state()
        # Force current_step to an invalid index that bypasses is_complete
        # by also setting a failed outcome so is_complete returns False
        # Actually, let's mock get_current_step directly
        with patch.object(state, "get_current_step", return_value=None), \
             patch.object(type(state), "is_complete", new_callable=lambda: property(lambda self: False)), \
             patch.object(type(state), "is_failed", new_callable=lambda: property(lambda self: False)):
            with pytest.raises(ActionableError) as exc_info:
                execute_workflow_step()

        assert "no more steps" in exc_info.value.message.lower()


class TestUnresolvedVariablePlaceholder:
    """Variable resolution when a placeholder has no matching value"""

    def test_unresolved_placeholder_left_intact(self, mock_file_system):
        """
        As a workflow orchestrator
        I need unresolved placeholders left as [VAR_NAME] in the prompt
        So that the LLM sees them and can report what's missing
        """
        from workflow_orchestrator_mcp.common.prompt_builder import _resolve_variables

        result = _resolve_variables(
            "Connect to [SERVER_NAME] on port [PORT]",
            {"SERVER_NAME": "prod-db"},
        )

        assert "prod-db" in result
        assert "[PORT]" in result  # Unresolved — left intact
