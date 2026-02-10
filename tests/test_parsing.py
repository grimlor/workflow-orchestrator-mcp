"""
Scenario Group 1: Workflow Loading and Parsing

Tests the public API: load_workflow()
Mocks only I/O: file system reads via pathlib.Path
"""

from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.common.error_handling import ActionableError
from workflow_orchestrator_mcp.tools.workflow_tools import load_workflow


class TestLoadWorkflowWithToolSpecifications:
    """Scenario 1.1: Load workflow with tool specifications"""

    def test_load_extracts_steps_with_tool_names(self, mock_file_system):
        """
        As a workflow author
        I need the parser to extract tool names from TOOL sections
        So that the orchestrator knows which tools each step requires
        """
        result = load_workflow("/path/to/workflow.md")

        assert result["success"] is True
        assert result["step_count"] == 3
        # Each step should have tool names populated
        first_step = result["first_step"]
        assert "tool_names" in first_step
        assert len(first_step["tool_names"]) > 0

    def test_load_returns_step_metadata(self, mock_file_system):
        """
        As a workflow author
        I need each step to include its name and description
        So that I can verify the parser understood my workflow
        """
        result = load_workflow("/path/to/workflow.md")

        first_step = result["first_step"]
        assert "name" in first_step
        assert "description" in first_step
        assert first_step["name"] != ""


class TestLoadWorkflowWithMultipleTools:
    """Scenario 1.2: Load workflow with multiple tools per step"""

    def test_multi_tool_step_has_ordered_list(self, mock_file_system):
        """
        As a workflow author
        I need multi-tool steps to preserve tool order
        So that the LLM invokes them in the correct sequence
        """
        load_workflow("/path/to/workflow.md")

        # The third step in valid_workflow_markdown uses TOOLS (plural)
        # We need to check it via load then state
        from workflow_orchestrator_mcp.common.workflow_state import get_state

        state = get_state()
        multi_tool_step = state.steps[2]  # "Create pull request"
        assert len(multi_tool_step.tool_names) == 2
        assert multi_tool_step.tool_names[0] == "get_current_branch"
        assert multi_tool_step.tool_names[1] == "create_pull_request"


class TestParseAssertionsFromWorkflow:
    """Scenario 1.3: Parse assertions from workflow"""

    def test_assertions_extracted_per_step(self, mock_file_system):
        """
        As a workflow author
        I need assertions to be extracted from ASSERT sections
        So that the LLM knows what success criteria to evaluate
        """
        load_workflow("/path/to/workflow.md")

        from workflow_orchestrator_mcp.common.workflow_state import get_state

        state = get_state()
        # Step 1 has 2 assertions
        assert len(state.steps[0].assertions) == 2
        assert 'result contains "repositories"' in state.steps[0].assertions
        assert "result.repositories.length > 0" in state.steps[0].assertions

    def test_assertions_associated_with_correct_step(self, mock_file_system):
        """
        As a workflow author
        I need assertions tied to the step they validate
        So that each step has its own success criteria
        """
        load_workflow("/path/to/workflow.md")

        from workflow_orchestrator_mcp.common.workflow_state import get_state

        state = get_state()
        # Step 2 has 1 assertion, step 3 has 2
        assert len(state.steps[1].assertions) == 1
        assert len(state.steps[2].assertions) == 2


class TestParseInputOutputSpecifications:
    """Scenario 1.4: Parse input/output specifications"""

    def test_inputs_define_required_variables(self, mock_file_system):
        """
        As a workflow author
        I need INPUTS sections parsed into variable requirements
        So that the orchestrator can validate variable availability
        """
        load_workflow("/path/to/workflow.md")

        from workflow_orchestrator_mcp.common.workflow_state import get_state

        state = get_state()
        # Step 2 ("Set repository context") has INPUTS
        step_with_inputs = state.steps[1]
        assert "REPO_NAME" in step_with_inputs.inputs
        assert step_with_inputs.inputs["REPO_NAME"] != ""

    def test_outputs_define_variable_mappings(self, mock_file_system):
        """
        As a workflow author
        I need OUTPUTS sections parsed into variable mappings
        So that step results can flow to subsequent steps
        """
        load_workflow("/path/to/workflow.md")

        from workflow_orchestrator_mcp.common.workflow_state import get_state

        state = get_state()
        # Step 1 has OUTPUT: result.repositories[0].name → REPO_NAME
        step_with_outputs = state.steps[0]
        assert "REPO_NAME" in step_with_outputs.outputs.values()


class TestRejectWorkflowWithoutToolSpecifications:
    """Scenario 1.5: Reject workflow without tool specifications"""

    def test_raises_actionable_error_for_missing_tools(self, workflow_without_tools):
        """
        As a workflow author
        I need clear feedback when I forget TOOL sections
        So that I can fix my workflow format
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=workflow_without_tools):
            with pytest.raises(ActionableError) as exc_info:
                load_workflow("/path/to/bad_workflow.md")

            assert "tool" in str(exc_info.value).lower()

    def test_raises_actionable_error_for_empty_workflow(self, empty_workflow_markdown):
        """
        As a workflow author
        I need feedback when no steps are found
        So that I know my file needs workflow step tags
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=empty_workflow_markdown):
            with pytest.raises(ActionableError):
                load_workflow("/path/to/empty.md")

    def test_raises_actionable_error_for_missing_file(self):
        """
        As a workflow author
        I need clear feedback when the file doesn't exist
        So that I can correct the path
        """
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(ActionableError) as exc_info:
                load_workflow("/nonexistent/path.md")

            assert "not found" in str(exc_info.value).lower()
