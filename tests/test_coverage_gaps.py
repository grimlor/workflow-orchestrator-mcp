"""
Coverage gap specifications

Tests for edge cases and alternate paths not covered by the primary scenario groups.
Each class specifies a behavioral contract for a specific boundary condition.

Spec classes:
    TestNoWorkflowLoadedGuard
    TestExecuteWorkflowStepGuards
    TestStepOutcomeAllAssertionsPassed
    TestParserEdgeCases
    TestUnresolvedVariablePlaceholder
    TestVersionFallbackOnMissingMetadata
    TestTemplateFileNotFound
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
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
    get_workflow_template,
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
            outputs = {"REPO_NAME": "test-repo"} if i == 0 else ({"PR_ID": "42"} if i == 2 else {})
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


class TestUnresolvedVariablePlaceholder:
    """
    REQUIREMENT: Unresolved variable placeholders are left intact in the prompt.

    WHO: The LLM consumer receiving prompts with partial variable resolution
    WHAT: When a step description contains a [PLACEHOLDER] that has no matching
          value in the variables dict, the placeholder passes through to the
          prompt unchanged; resolved placeholders are replaced with their values
    WHY: Leaving unresolved placeholders visible lets the LLM report
         what's missing instead of silently dropping the reference

    MOCK BOUNDARY:
        Mock:  filesystem via patch (pathlib.Path I/O for workflow loading)
        Real:  execute_workflow_step, variable resolution, WorkflowState
        Never: Call _resolve_variables directly — test through execute_workflow_step
    """

    def test_undeclared_placeholder_passes_through_to_prompt(self) -> None:
        """
        Given a workflow step whose description contains an undeclared placeholder
        When execute_workflow_step is called
        Then the undeclared placeholder appears unchanged in the prompt
        """
        # Given: a workflow whose step description references [DEPLOY_TARGET]
        #        which is NOT declared as an INPUT and has no value
        workflow_with_undeclared_placeholder = """# Placeholder Workflow

### 🔧 WORKFLOW STEP: Deploy to environment
```
Deploy the application to [DEPLOY_TARGET] environment and verify health check.
```

### 🛠️ TOOL: deploy_tool

### ✅ ASSERT:
- deployment succeeded
"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=workflow_with_undeclared_placeholder),
        ):
            load_workflow("/path/to/placeholder.md")

        # When: execute_workflow_step is called
        result = execute_workflow_step()

        # Then: the undeclared placeholder passes through unchanged
        prompt = result["prompt"]
        assert "[DEPLOY_TARGET]" in prompt, (
            f"Expected undeclared placeholder '[DEPLOY_TARGET]' to remain intact in prompt, "
            f"got: {prompt[:200]}"
        )


class TestVersionFallbackOnMissingMetadata:
    """
    REQUIREMENT: The package exposes a version string even without installed metadata.

    WHO: Developers using editable installs or CI environments before build
    WHAT: When importlib.metadata cannot find the package, __version__ falls
          back to "0.0.0+unknown" rather than raising PackageNotFoundError
    WHY: Code that reads __version__ (logging, CLI --version, debug output)
         must not crash when the package metadata is unavailable

    MOCK BOUNDARY:
        Mock:  importlib.metadata.version (simulates missing package metadata)
        Real:  The importlib machinery that triggers the fallback
        Never: Set __version__ directly — always trigger via the import mechanism
    """

    def test_version_falls_back_when_metadata_unavailable(self) -> None:
        """
        Given the package metadata is not available
        When the package is imported
        Then __version__ is "0.0.0+unknown"
        """
        # Given: importlib.metadata.version raises PackageNotFoundError
        import importlib  # noqa: PLC0415  # must import after sys.modules manipulation
        from importlib.metadata import (  # noqa: PLC0415  # must import after sys.modules manipulation
            PackageNotFoundError,
        )

        import workflow_orchestrator_mcp  # noqa: PLC0415  # must import after sys.modules manipulation

        with patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError("workflow-orchestrator-mcp"),
        ):
            # When: the package is re-imported
            importlib.reload(workflow_orchestrator_mcp)

            # Then: version falls back
            assert workflow_orchestrator_mcp.__version__ == "0.0.0+unknown", (
                f"Expected '0.0.0+unknown' fallback, got '{workflow_orchestrator_mcp.__version__}'"
            )

        # Restore normal state
        importlib.reload(workflow_orchestrator_mcp)


class TestTemplateFileNotFound:
    """
    REQUIREMENT: get_workflow_template raises an actionable error when the
    template file cannot be found at the given path.

    WHO: Any caller passing a template_path to get_workflow_template
    WHAT: A nonexistent path raises WorkflowError with a message naming
          the missing file and a suggestion to re-install
    WHY: A generic FileNotFoundError gives the caller no remediation path —
         the actionable error tells them exactly what to do

    MOCK BOUNDARY:
        Mock:  nothing — uses a real nonexistent path on the filesystem
        Real:  get_workflow_template function, WorkflowError construction
        Never: Patch pathlib or read_text — use a genuinely missing path
    """

    def test_nonexistent_template_path_raises_actionable_error(self) -> None:
        """
        Given a template_path pointing to a file that does not exist
        When get_workflow_template is called
        Then a WorkflowError is raised naming the missing file
        """
        # Given: a path that does not exist
        bad_path = Path("/nonexistent/workflow_template.md")

        # When / Then: calling with the bad path raises WorkflowError
        with pytest.raises(WorkflowError) as exc_info:
            get_workflow_template(template_path=bad_path)

        assert "not found" in str(exc_info.value).lower(), (
            f"Error should mention 'not found'. Got: {exc_info.value}"
        )
        assert str(bad_path) in str(exc_info.value), (
            f"Error should name the missing path '{bad_path}'. Got: {exc_info.value}"
        )
