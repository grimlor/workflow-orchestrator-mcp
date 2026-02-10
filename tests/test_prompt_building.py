"""
Scenario Group 2: Enriched Prompt Building

Tests the public API: execute_workflow_step()
Relies on load_workflow() to populate state, so uses pre-loaded state helper.
"""


import pytest

from workflow_orchestrator_mcp.common.workflow_state import get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
)


@pytest.fixture
def loaded_workflow(mock_file_system):
    """Load a valid workflow and return the state for prompt-building tests"""
    load_workflow("/path/to/workflow.md")
    return get_state()


class TestBuildEnrichedPromptForSingleTool:
    """Scenario 2.1: Build enriched prompt for single-tool step"""

    def test_prompt_includes_step_description(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the enriched prompt to include the step description
        So that the LLM understands what it needs to do
        """
        result = execute_workflow_step()

        assert "prompt" in result
        prompt = result["prompt"]
        assert "Find all repositories" in prompt

    def test_prompt_names_the_tool(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the enriched prompt to name the tool
        So that the LLM knows which tool to invoke
        """
        result = execute_workflow_step()

        prompt = result["prompt"]
        assert "repository_discovery" in prompt

    def test_prompt_includes_assertion_criteria(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the enriched prompt to include assertion criteria
        So that the LLM knows what to verify
        """
        result = execute_workflow_step()

        prompt = result["prompt"]
        assert "repositories" in prompt.lower()


class TestBuildEnrichedPromptForMultiTool:
    """Scenario 2.2: Build enriched prompt for multi-tool step"""

    def test_prompt_lists_all_tools_in_order(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the enriched prompt to list multiple tools
        So that the LLM invokes them in the correct sequence
        """
        # Advance to step 3 (multi-tool step) by recording outcomes for steps 1 & 2
        from workflow_orchestrator_mcp.common.workflow_state import StepOutcome, StepStatus

        state = loaded_workflow
        state.record_step_outcome(StepOutcome(
            step_number=0, status=StepStatus.PASSED,
            output_variables={"REPO_NAME": "my-repo"},
        ))
        state.current_step = 1
        state.record_step_outcome(StepOutcome(
            step_number=1, status=StepStatus.PASSED,
        ))
        state.current_step = 2

        result = execute_workflow_step()

        prompt = result["prompt"]
        # Both tools should appear in the prompt
        assert "get_current_branch" in prompt
        assert "create_pull_request" in prompt
        # Order should be preserved (get_current_branch before create_pull_request)
        assert prompt.index("get_current_branch") < prompt.index("create_pull_request")


class TestIncludeResolvedVariablesInPrompt:
    """Scenario 2.3: Include resolved variables in enriched prompt"""

    def test_variable_placeholders_replaced(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need variable placeholders resolved in the prompt
        So that the LLM has concrete values to work with
        """
        from workflow_orchestrator_mcp.common.workflow_state import StepOutcome, StepStatus

        state = loaded_workflow
        # Step 1 produces REPO_NAME
        state.record_step_outcome(StepOutcome(
            step_number=0, status=StepStatus.PASSED,
            output_variables={"REPO_NAME": "my-repo"},
        ))
        state.current_step = 1

        result = execute_workflow_step()

        prompt = result["prompt"]
        # The step 2 description has [REPO_NAME] — should be resolved
        assert "my-repo" in prompt
        # The raw placeholder should NOT appear
        assert "[REPO_NAME]" not in prompt


class TestPromptIncludesCallbackInstructions:
    """Scenario 2.4: Prompt includes callback instructions"""

    def test_prompt_instructs_report_step_result(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the prompt to instruct the LLM to call report_step_result
        So that the orchestrator gets feedback on execution outcomes
        """
        result = execute_workflow_step()

        prompt = result["prompt"]
        assert "report_step_result" in prompt

    def test_prompt_specifies_expected_assertion_count(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the prompt to tell the LLM how many assertions to evaluate
        So that the feedback includes results for all criteria
        """
        result = execute_workflow_step()

        prompt = result["prompt"]
        # Step 1 has 2 assertions
        assert "2" in prompt

    def test_prompt_specifies_output_variable_names(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need the prompt to name expected output variables
        So that the LLM extracts and reports the right values
        """
        result = execute_workflow_step()

        prompt = result["prompt"]
        # Step 1 outputs REPO_NAME
        assert "REPO_NAME" in prompt
