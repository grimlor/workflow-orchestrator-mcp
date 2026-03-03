"""
Coverage gap specifications

Tests for edge cases and alternate paths not covered by the primary scenario groups.
Each class specifies a behavioral contract for a specific boundary condition.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
from workflow_orchestrator_mcp.common.prompt_builder import _resolve_variables  # noqa: PLC2701
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
    """
    REQUIREMENT: Operations on workflow state before loading produce actionable errors.

    WHO: The workflow user invoking tools before loading a workflow
    WHAT: get_workflow_state, reset_workflow, and require_loaded_workflow all
          raise WorkflowError with a message that names the action needed
          ("load_workflow") when no workflow is loaded
    WHY: Silent failures or generic exceptions leave the user guessing —
         the error must tell them exactly what to do next

    MOCK BOUNDARY:
        Mock: nothing — these tests exercise guard logic with no I/O
        Real:  workflow_tools functions, require_loaded_workflow guard
        Never: Pre-populate global state — the point is that state is empty
    """

    def test_get_workflow_state_raises_when_nothing_loaded(self) -> None:
        """
        When get_workflow_state is called before any workflow is loaded
        Then a WorkflowError is raised mentioning "no workflow has been loaded"
        """
        # Given: no workflow has been loaded (clean state)

        # When: get_workflow_state is called
        with pytest.raises(WorkflowError) as exc_info:
            get_workflow_state()

        # Then: the error message mentions no workflow loaded
        assert "no workflow has been loaded" in str(exc_info.value).lower(), (
            f"Expected 'no workflow has been loaded' in error, got: {exc_info.value}"
        )

    def test_reset_workflow_raises_when_nothing_loaded(self) -> None:
        """
        When reset_workflow is called before any workflow is loaded
        Then a WorkflowError is raised mentioning "no workflow has been loaded"
        """
        # Given: no workflow has been loaded (clean state)

        # When: reset_workflow is called
        with pytest.raises(WorkflowError) as exc_info:
            reset_workflow()

        # Then: the error message mentions no workflow loaded
        assert "no workflow has been loaded" in str(exc_info.value).lower(), (
            f"Expected 'no workflow has been loaded' in error, got: {exc_info.value}"
        )

    def test_require_loaded_workflow_raises_actionable_error(self) -> None:
        """
        When require_loaded_workflow is called with no workflow loaded
        Then a WorkflowError is raised whose suggestion mentions "load_workflow"
        """
        # Given: no workflow has been loaded (clean state)

        # When: the guard function is called
        with pytest.raises(WorkflowError) as exc_info:
            require_loaded_workflow()

        # Then: the suggestion mentions load_workflow
        err = exc_info.value
        assert "load_workflow" in (err.suggestion or "").lower(), (
            f"Expected suggestion to mention 'load_workflow'. "
            f"Got error='{err.error}', suggestion='{err.suggestion}'"
        )


class TestExecuteWorkflowStepGuards:
    """
    REQUIREMENT: execute_workflow_step rejects calls when the workflow is in a terminal state.

    WHO: The workflow user attempting to execute steps after completion or failure
    WHAT: Calling execute_workflow_step when the workflow is complete raises
          a WorkflowError mentioning "complete"; calling it when the workflow
          has failed raises a WorkflowError mentioning "failed"
    WHY: Executing steps in a terminal state would produce undefined behavior —
         the error must tell the user to reset before retrying

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, workflow_tools functions
        Never: Set is_complete or is_failed directly — always reach terminal state via execution
    """

    def test_raises_when_workflow_is_complete(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow where all steps have been executed and passed
        When execute_workflow_step is called again
        Then a WorkflowError is raised mentioning "complete"
        """
        # Given: a workflow where all steps have passed
        load_workflow("/path/to/workflow.md")
        state = get_state()

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

        assert state.is_complete, (
            f"Expected workflow to be complete after all steps, got is_complete={state.is_complete}"
        )

        # When: execute_workflow_step is called again
        with pytest.raises(WorkflowError) as exc_info:
            execute_workflow_step()

        # Then: the error mentions "complete"
        assert "complete" in str(exc_info.value).lower(), (
            f"Expected 'complete' in error message, got: {exc_info.value}"
        )

    def test_raises_when_workflow_has_failed(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow where a step has failed
        When execute_workflow_step is called again
        Then a WorkflowError is raised mentioning "failed"
        """
        # Given: a workflow where step 1 has failed
        load_workflow("/path/to/workflow.md")

        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="failed",
            error_message="Tool not available",
        )

        state = get_state()
        assert state.is_failed, (
            f"Expected workflow to be failed after step failure, got is_failed={state.is_failed}"
        )

        # When: execute_workflow_step is called again
        with pytest.raises(WorkflowError) as exc_info:
            execute_workflow_step()

        # Then: the error mentions "failed"
        assert "failed" in str(exc_info.value).lower(), (
            f"Expected 'failed' in error message, got: {exc_info.value}"
        )


class TestStepOutcomeAllAssertionsPassed:
    """
    REQUIREMENT: StepOutcome.all_assertions_passed accurately reflects assertion results.

    WHO: The workflow orchestrator making pass/fail decisions
    WHAT: Returns True when all assertions passed, False when any failed,
          and True (vacuously) when no assertions exist
    WHY: An incorrect all_assertions_passed value would cause the orchestrator
         to misclassify step outcomes, silently passing failures or failing successes

    MOCK BOUNDARY:
        Mock: nothing — this class tests pure computation
        Real:  StepOutcome, AssertionResult dataclasses
        Never: Mock all_assertions_passed — it is the subject under test
    """

    def test_true_when_all_pass(self) -> None:
        """
        Given a step outcome where all assertions passed
        When all_assertions_passed is checked
        Then it returns True
        """
        # Given: a step outcome with all assertions passed
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.PASSED,
            assertion_results=[
                AssertionResult(assertion="a > 0", passed=True),
                AssertionResult(assertion="b > 0", passed=True),
            ],
        )

        # When/Then: all_assertions_passed is True
        assert outcome.all_assertions_passed is True, (
            f"Expected all_assertions_passed=True when all pass, got {outcome.all_assertions_passed}"
        )

    def test_false_when_any_fails(self) -> None:
        """
        Given a step outcome where one assertion failed
        When all_assertions_passed is checked
        Then it returns False
        """
        # Given: a step outcome with one failed assertion
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.FAILED,
            assertion_results=[
                AssertionResult(assertion="a > 0", passed=True),
                AssertionResult(assertion="b > 0", passed=False, detail="was 0"),
            ],
        )

        # When/Then: all_assertions_passed is False
        assert outcome.all_assertions_passed is False, (
            f"Expected all_assertions_passed=False when any fails, got {outcome.all_assertions_passed}"
        )

    def test_true_when_no_assertions(self) -> None:
        """
        Given a step outcome with no assertions
        When all_assertions_passed is checked
        Then it returns True (vacuously)
        """
        # Given: a step outcome with no assertions
        outcome = StepOutcome(
            step_number=0,
            status=StepStatus.PASSED,
            assertion_results=[],
        )

        # When/Then: all_assertions_passed is vacuously True
        assert outcome.all_assertions_passed is True, (
            f"Expected all_assertions_passed=True for empty assertions (vacuous truth), "
            f"got {outcome.all_assertions_passed}"
        )


class TestParserEdgeCases:
    """
    REQUIREMENT: The parser handles filesystem errors and alternate syntax gracefully.

    WHO: The workflow author encountering file access issues or using alternate syntax
    WHAT: A file read error (permissions, encoding) raises a WorkflowError
          mentioning "failed to read"; ASCII arrow (->) in OUTPUTS is accepted
          alongside the Unicode arrow (→)
    WHY: Unhandled I/O exceptions crash the server; rejecting ASCII arrows
         forces authors to use special characters unnecessarily

    MOCK BOUNDARY:
        Mock:  filesystem via patch (pathlib.Path.exists, pathlib.Path.read_text)
        Real:  workflow parser, WorkflowError construction
        Never: Bypass the parser — always trigger via load_workflow
    """

    def test_file_read_error_raises_actionable_error(self) -> None:
        """
        Given a file path that exists but cannot be read (e.g., permissions)
        When the workflow is loaded
        Then a WorkflowError is raised mentioning "failed to read"
        """
        # Given: a file that exists but raises PermissionError on read
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")),
        ):
            # When: the workflow is loaded
            with pytest.raises(WorkflowError) as exc_info:
                load_workflow("/path/to/unreadable.md")

            # Then: the error mentions failed to read
            assert "failed to read" in str(exc_info.value).lower(), (
                f"Expected 'failed to read' in error message, got: {exc_info.value}"
            )

    def test_ascii_arrow_in_outputs(self) -> None:
        """
        Given a workflow using ASCII arrow (->) in OUTPUTS instead of Unicode (→)
        When the workflow is loaded
        Then the output variable mapping is parsed correctly
        """
        # Given: a workflow with ASCII arrow syntax
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
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=workflow_with_ascii_arrow),
        ):
            load_workflow("/path/to/ascii.md")

        # When: the parsed state is inspected
        state = get_state()
        step = state.steps[0]

        # Then: the output variable mapping is correct
        assert "ENTITY_ID" in step.outputs.values(), (
            f"Expected 'ENTITY_ID' in output values, got: {list(step.outputs.values())}"
        )
        assert "result.id" in step.outputs, (
            f"Expected 'result.id' in output keys, got: {list(step.outputs.keys())}"
        )


class TestExecuteWorkflowStepDefensiveGuard:
    """
    REQUIREMENT: A safety net catches the impossible case where get_current_step
                 returns None after guards pass.

    WHO: The workflow orchestrator runtime
    WHAT: If get_current_step() returns None despite is_complete and is_failed
          both being False, a WorkflowError is raised mentioning "no more steps"
    WHY: This defensive guard prevents a NoneType crash in production if
         state invariants are violated by a future code change

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O);
               get_current_step, is_complete, is_failed patched to simulate impossible state
        Real:  execute_workflow_step guard logic
        Never: Skip the guard — it is the subject under test
    """

    def test_step_none_after_guards_pass_raises_actionable_error(
        self, mock_file_system: tuple[Any, Any]
    ) -> None:
        """
        Given a workflow where get_current_step returns None despite guards passing
        When execute_workflow_step is called
        Then a WorkflowError is raised mentioning "no more steps"
        """
        # Given: a loaded workflow with patched state to simulate impossible condition
        load_workflow("/path/to/workflow.md")
        state = get_state()

        with (
            patch.object(state, "get_current_step", return_value=None),
            patch.object(
                type(state), "is_complete", new_callable=lambda: property(lambda self: False)
            ),
            patch.object(
                type(state), "is_failed", new_callable=lambda: property(lambda self: False)
            ),
            # When: execute_workflow_step is called
            pytest.raises(WorkflowError) as exc_info,
        ):
            execute_workflow_step()

        # Then: the error mentions "no more steps"
        assert "no more steps" in exc_info.value.error.lower(), (
            f"Expected 'no more steps' in error, got: {exc_info.value.error}"
        )


class TestUnresolvedVariablePlaceholder:
    """
    REQUIREMENT: Unresolved variable placeholders are left intact in the prompt.

    WHO: The workflow orchestrator building prompts for the LLM
    WHAT: When a placeholder like [VAR_NAME] has no matching value in the
          variables dict, it is left as-is in the resolved string;
          resolved placeholders are replaced with their values
    WHY: Leaving unresolved placeholders visible lets the LLM report
         what's missing instead of silently dropping the reference

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  _resolve_variables function (pure string transformation)
        Never: Mock the regex — the substitution logic is the subject under test
    """

    def test_unresolved_placeholder_left_intact(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a prompt with two placeholders where only one has a value
        When _resolve_variables is called
        Then the resolved placeholder is replaced and the unresolved one remains
        """
        # Given: a prompt with [SERVER_NAME] (resolved) and [PORT] (unresolved)
        result = _resolve_variables(
            "Connect to [SERVER_NAME] on port [PORT]",
            {"SERVER_NAME": "prod-db"},
        )

        # Then: resolved placeholder is replaced, unresolved is left intact
        assert "prod-db" in result, (
            f"Expected resolved placeholder 'prod-db' in result, got: {result}"
        )
        assert "[PORT]" in result, (
            f"Expected unresolved placeholder '[PORT]' to remain intact, got: {result}"
        )
