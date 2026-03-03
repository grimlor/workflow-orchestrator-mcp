"""BDD specs for workflow loading and parsing.

Covers: TestLoadWorkflowWithToolSpecifications,
        TestLoadWorkflowWithMultipleTools,
        TestParseAssertionsFromWorkflow,
        TestParseInputOutputSpecifications,
        TestRejectWorkflowWithoutToolSpecifications
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
from workflow_orchestrator_mcp.common.workflow_state import get_state
from workflow_orchestrator_mcp.tools.workflow_tools import load_workflow


class TestLoadWorkflowWithToolSpecifications:
    """
    REQUIREMENT: Parsed workflow steps include extracted tool names and metadata.

    WHO: The orchestrator engine consuming parsed workflow steps
    WHAT: Each parsed step carries its tool name list and descriptive metadata
          (name, description) so the orchestrator can dispatch correctly
    WHY: Without tool names the orchestrator cannot invoke the right MCP tools;
         without metadata the user cannot verify their workflow was understood

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (pathlib.Path.exists / read_text)
        Real:  load_workflow parser logic, WorkflowState
        Never: Construct step dicts directly — always obtain via load_workflow
    """

    def test_load_extracts_steps_with_tool_names(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a valid workflow file is loaded
        Then the result reports success with the correct step count
             and each step contains a non-empty tool_names list
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        result = load_workflow("/path/to/workflow.md")

        # Then: the result indicates success with expected step count and tool names
        assert result["success"] is True, (
            f"Expected success=True, got {result['success']}"
        )
        assert result["step_count"] == 3, (
            f"Expected 3 steps, got {result['step_count']}"
        )
        first_step = result["first_step"]
        assert "tool_names" in first_step, (
            f"Expected 'tool_names' key in first_step, got keys: {list(first_step.keys())}"
        )
        assert len(first_step["tool_names"]) > 0, (
            f"Expected at least one tool name, got {first_step['tool_names']}"
        )

    def test_load_returns_step_metadata(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a valid workflow file is loaded
        Then each step includes a non-empty name and a description
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        result = load_workflow("/path/to/workflow.md")

        # Then: the first step has name and description metadata
        first_step = result["first_step"]
        assert "name" in first_step, (
            f"Expected 'name' key in first_step, got keys: {list(first_step.keys())}"
        )
        assert "description" in first_step, (
            f"Expected 'description' key in first_step, got keys: {list(first_step.keys())}"
        )
        assert first_step["name"] != "", (
            "Expected non-empty step name, got empty string"
        )


class TestLoadWorkflowWithMultipleTools:
    """
    REQUIREMENT: Multi-tool steps preserve declared tool order.

    WHO: The orchestrator dispatching tools within a single step
    WHAT: When a step declares multiple tools via TOOLS (plural), the parsed
          tool_names list preserves the authored order
    WHY: Tool invocation order may matter for side-effects; reordering could
         cause the LLM to invoke tools in the wrong sequence

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (pathlib.Path.exists / read_text)
        Real:  load_workflow parser logic, WorkflowState
        Never: Construct Step objects directly — always obtain via load_workflow + get_state
    """

    def test_multi_tool_step_has_ordered_list(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a workflow with a multi-tool step is loaded
        Then the step's tool_names list contains both tools in declared order
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        load_workflow("/path/to/workflow.md")

        # Then: the third step ("Create pull request") has exactly 2 tools in order
        # The third step in valid_workflow_markdown uses TOOLS (plural)
        state = get_state()
        multi_tool_step = state.steps[2]  # "Create pull request"
        assert len(multi_tool_step.tool_names) == 2, (
            f"Expected 2 tool names, got {len(multi_tool_step.tool_names)}: "
            f"{multi_tool_step.tool_names}"
        )
        assert multi_tool_step.tool_names[0] == "get_current_branch", (
            f"Expected first tool 'get_current_branch', got '{multi_tool_step.tool_names[0]}'"
        )
        assert multi_tool_step.tool_names[1] == "create_pull_request", (
            f"Expected second tool 'create_pull_request', got '{multi_tool_step.tool_names[1]}'"
        )


class TestParseAssertionsFromWorkflow:
    """
    REQUIREMENT: ASSERT sections are extracted and associated per step.

    WHO: The orchestrator evaluating step success criteria
    WHAT: Each step's ASSERT section is parsed into an assertions list;
          assertions are associated with the correct step, not merged globally
    WHY: Step-level assertions enable per-step pass/fail evaluation;
         misassociated assertions would validate the wrong step's output

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (pathlib.Path.exists / read_text)
        Real:  load_workflow parser logic, WorkflowState
        Never: Construct Step objects directly — always obtain via load_workflow + get_state
    """

    def test_assertions_extracted_per_step(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a workflow with ASSERT sections is loaded
        Then step 1 contains exactly 2 assertions with the expected text
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        load_workflow("/path/to/workflow.md")

        # Then: step 1 has 2 assertions with expected content
        state = get_state()
        assert len(state.steps[0].assertions) == 2, (
            f"Expected 2 assertions on step 0, got {len(state.steps[0].assertions)}: "
            f"{state.steps[0].assertions}"
        )
        assert 'result contains "repositories"' in state.steps[0].assertions, (
            f"Expected 'result contains \"repositories\"' in assertions, "
            f"got {state.steps[0].assertions}"
        )
        assert "result.repositories.length > 0" in state.steps[0].assertions, (
            f"Expected 'result.repositories.length > 0' in assertions, "
            f"got {state.steps[0].assertions}"
        )

    def test_assertions_associated_with_correct_step(
        self, mock_file_system: tuple[Any, Any]
    ) -> None:
        """
        When a workflow with per-step ASSERT sections is loaded
        Then each step carries only its own assertions
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        load_workflow("/path/to/workflow.md")

        # Then: step 2 has 1 assertion, step 3 has 2 assertions
        state = get_state()
        assert len(state.steps[1].assertions) == 1, (
            f"Expected 1 assertion on step 1, got {len(state.steps[1].assertions)}: "
            f"{state.steps[1].assertions}"
        )
        assert len(state.steps[2].assertions) == 2, (
            f"Expected 2 assertions on step 2, got {len(state.steps[2].assertions)}: "
            f"{state.steps[2].assertions}"
        )


class TestParseInputOutputSpecifications:
    """
    REQUIREMENT: INPUT/OUTPUT sections are parsed into variable requirements and mappings.

    WHO: The orchestrator resolving inter-step variable flow
    WHAT: INPUTS sections produce a dict of required variable names;
          OUTPUTS sections produce variable mappings so results flow between steps
    WHY: Without parsed inputs the orchestrator cannot validate variable availability;
         without parsed outputs step results cannot propagate to downstream steps

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (pathlib.Path.exists / read_text)
        Real:  load_workflow parser logic, WorkflowState
        Never: Construct Step objects directly — always obtain via load_workflow + get_state
    """

    def test_inputs_define_required_variables(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a workflow with INPUTS sections is loaded
        Then the step's inputs dict contains the declared variable names
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        load_workflow("/path/to/workflow.md")

        # Then: step 2 ("Set repository context") has REPO_NAME in inputs
        state = get_state()
        step_with_inputs = state.steps[1]
        assert "REPO_NAME" in step_with_inputs.inputs, (
            f"Expected 'REPO_NAME' in inputs, got keys: {list(step_with_inputs.inputs.keys())}"
        )
        assert step_with_inputs.inputs["REPO_NAME"] != "", (
            "Expected non-empty REPO_NAME input description, got empty string"
        )

    def test_outputs_define_variable_mappings(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a workflow with OUTPUTS sections is loaded
        Then the step's outputs dict maps expressions to variable names
        """
        # Given: a valid workflow file available via mock_file_system fixture

        # When: the workflow is loaded
        load_workflow("/path/to/workflow.md")

        # Then: step 1 has REPO_NAME in its output variable mappings
        state = get_state()
        step_with_outputs = state.steps[0]
        assert "REPO_NAME" in step_with_outputs.outputs.values(), (
            f"Expected 'REPO_NAME' in output values, got: {dict(step_with_outputs.outputs)}"
        )


class TestRejectWorkflowWithoutToolSpecifications:
    """
    REQUIREMENT: Invalid or missing workflows produce actionable errors.

    WHO: The workflow author iterating on workflow files
    WHAT: Missing TOOL sections, empty workflows, and non-existent file paths
          each raise a WorkflowError with a message describing the problem
    WHY: Without actionable error messages the author cannot diagnose why their
         workflow failed to load

    MOCK BOUNDARY:
        Mock:  pathlib.Path.exists / read_text (patched inline per test)
        Real:  load_workflow parser logic, WorkflowError raising
        Never: Construct WorkflowError directly — always obtain via load_workflow
    """

    def test_raises_actionable_error_for_missing_tools(self, workflow_without_tools: str) -> None:
        """
        Given a workflow file that has steps but no TOOL sections
        When the workflow is loaded
        Then a WorkflowError is raised whose message mentions "tool"
        """
        # Given: a workflow markdown without TOOL sections
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=workflow_without_tools),
            pytest.raises(WorkflowError) as exc_info,
        ):
            # When: the workflow is loaded
            load_workflow("/path/to/bad_workflow.md")

            # Then: the error message mentions "tool"
            assert "tool" in str(exc_info.value).lower(), (
                f"Expected 'tool' in error message, got: {exc_info.value}"
            )

    def test_raises_actionable_error_for_empty_workflow(
        self, empty_workflow_markdown: str
    ) -> None:
        """
        Given a markdown file with no workflow steps
        When the workflow is loaded
        Then a WorkflowError is raised whose message describes the empty workflow
        """
        # Given: an empty workflow markdown
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=empty_workflow_markdown),
        ):
            # When: the workflow is loaded
            with pytest.raises(WorkflowError) as exc_info:
                load_workflow("/path/to/empty.md")

            # Then: the error message describes the problem
            error = str(exc_info.value).lower()
            assert "step" in error or "empty" in error or "no" in error, (
                f"Expected error to mention 'step', 'empty', or 'no', got: {exc_info.value}"
            )

    def test_raises_actionable_error_for_missing_file(self) -> None:
        """
        Given a file path that does not exist on disk
        When the workflow is loaded
        Then a WorkflowError is raised whose message contains "not found"
        """
        # Given: a non-existent file path
        with patch("pathlib.Path.exists", return_value=False):
            # When: the workflow is loaded
            with pytest.raises(WorkflowError) as exc_info:
                load_workflow("/nonexistent/path.md")

            # Then: the error message mentions "not found"
            assert "not found" in str(exc_info.value).lower(), (
                f"Expected 'not found' in error message, got: {exc_info.value}"
            )
