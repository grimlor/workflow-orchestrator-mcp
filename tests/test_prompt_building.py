"""
Enriched prompt building tests.

Covers BDD spec classes:
- TestBuildEnrichedPromptForSingleTool
- TestBuildEnrichedPromptForMultiTool
- TestIncludeResolvedVariablesInPrompt
- TestPromptIncludesCallbackInstructions

Tests the public API: execute_workflow_step()
Relies on load_workflow() to populate state, so uses pre-loaded state helper.
"""

from __future__ import annotations

from typing import Any

import pytest

from workflow_orchestrator_mcp.common.workflow_state import (
    StepOutcome,
    StepStatus,
    WorkflowState,
    get_state,
)
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
)


@pytest.fixture
def loaded_workflow(mock_file_system: tuple[Any, Any]) -> WorkflowState:
    """Load a valid workflow and return the state for prompt-building tests"""
    load_workflow("/path/to/workflow.md")
    return get_state()


class TestBuildEnrichedPromptForSingleTool:
    """
    REQUIREMENT: Enriched prompt for a single-tool step contains description,
    tool name, and assertion criteria.

    WHO: The LLM consumer receiving the prompt from execute_workflow_step
    WHAT: The prompt includes the step description so the LLM understands the
          task; the prompt names the tool so the LLM knows which tool to invoke;
          the prompt includes assertion criteria so the LLM knows what to verify
    WHY: Without a complete prompt the LLM cannot autonomously execute a
         workflow step or validate its own output

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O for workflow loading)
        Real:  execute_workflow_step, WorkflowState, prompt construction logic
        Never: Construct prompt strings directly — always obtain via execute_workflow_step()
    """

    def test_prompt_includes_step_description(self, loaded_workflow: WorkflowState) -> None:
        """
        When execute_workflow_step is called for a single-tool step
        Then the prompt includes the step description text
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the result contains a prompt with the step description
        assert "prompt" in result, (
            f"Expected 'prompt' key in result, got keys: {list(result.keys())}"
        )
        prompt = result["prompt"]
        assert "Find all repositories" in prompt, (
            f"Expected step description 'Find all repositories' in prompt, got: {prompt[:200]}"
        )

    def test_prompt_names_the_tool(self, loaded_workflow: WorkflowState) -> None:
        """
        When execute_workflow_step is called for a single-tool step
        Then the prompt names the tool to invoke
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the prompt contains the tool name
        prompt = result["prompt"]
        assert "repository_discovery" in prompt, (
            f"Expected tool name 'repository_discovery' in prompt, got: {prompt[:200]}"
        )

    def test_prompt_includes_assertion_criteria(self, loaded_workflow: WorkflowState) -> None:
        """
        When execute_workflow_step is called for a single-tool step
        Then the prompt includes assertion criteria for verification
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the prompt references the assertion subject
        prompt = result["prompt"]
        assert "repositories" in prompt.lower(), (
            f"Expected 'repositories' (case-insensitive) in prompt, got: {prompt[:200]}"
        )


class TestBuildEnrichedPromptForMultiTool:
    """
    REQUIREMENT: Enriched prompt for a multi-tool step lists all tools in
    their declared order.

    WHO: The LLM consumer receiving a multi-tool prompt
    WHAT: The prompt lists all tools for the step and preserves their
          declared sequence so the LLM invokes them in the correct order
    WHY: Out-of-order tool invocation can cause data dependencies to fail
         (e.g., creating a PR before checking the current branch)

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O for workflow loading)
        Real:  execute_workflow_step, WorkflowState, step advancement logic
        Never: Construct prompt strings directly — always obtain via execute_workflow_step()
    """

    def test_prompt_lists_all_tools_in_order(self, loaded_workflow: WorkflowState) -> None:
        """
        Given steps 1 and 2 have been completed successfully
        When execute_workflow_step is called for the multi-tool step 3
        Then the prompt lists all tools in their declared order
        """
        # Given: advance to step 3 (multi-tool step) by recording outcomes for steps 1 & 2
        state = loaded_workflow
        state.record_step_outcome(
            StepOutcome(
                step_number=0,
                status=StepStatus.PASSED,
                output_variables={"REPO_NAME": "my-repo"},
            )
        )
        state.current_step = 1
        state.record_step_outcome(
            StepOutcome(
                step_number=1,
                status=StepStatus.PASSED,
            )
        )
        state.current_step = 2

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: both tools appear in the prompt in declared order
        prompt = result["prompt"]
        assert "get_current_branch" in prompt, (
            f"Expected 'get_current_branch' in prompt, got: {prompt[:300]}"
        )
        assert "create_pull_request" in prompt, (
            f"Expected 'create_pull_request' in prompt, got: {prompt[:300]}"
        )
        assert prompt.index("get_current_branch") < prompt.index("create_pull_request"), (
            "Expected get_current_branch before create_pull_request in prompt, "
            f"but get_current_branch at {prompt.index('get_current_branch')} "
            f"and create_pull_request at {prompt.index('create_pull_request')}"
        )


class TestIncludeResolvedVariablesInPrompt:
    """
    REQUIREMENT: Variable placeholders in the prompt are resolved to their
    concrete values from prior step outcomes.

    WHO: The LLM consumer that needs concrete values, not abstract placeholders
    WHAT: Placeholders like [REPO_NAME] are replaced with the actual value
          produced by a prior step; raw placeholders do not appear in the prompt
    WHY: Unresolved placeholders cause the LLM to hallucinate values or fail
         to execute the step correctly

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O for workflow loading)
        Real:  execute_workflow_step, WorkflowState, variable resolution logic
        Never: Construct prompt strings directly — always obtain via execute_workflow_step()
    """

    def test_variable_placeholders_replaced(self, loaded_workflow: WorkflowState) -> None:
        """
        Given step 1 produced REPO_NAME="my-repo"
        When execute_workflow_step is called for the step that references [REPO_NAME]
        Then the prompt contains the resolved value and no raw placeholder
        """
        # Given: step 1 produces REPO_NAME
        state = loaded_workflow
        state.record_step_outcome(
            StepOutcome(
                step_number=0,
                status=StepStatus.PASSED,
                output_variables={"REPO_NAME": "my-repo"},
            )
        )
        state.current_step = 1

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the resolved value appears and the raw placeholder does not
        prompt = result["prompt"]
        assert "my-repo" in prompt, (
            f"Expected resolved value 'my-repo' in prompt, got: {prompt[:200]}"
        )
        assert "[REPO_NAME]" not in prompt, (
            f"Raw placeholder [REPO_NAME] should not appear in prompt, got: {prompt[:200]}"
        )


class TestPromptIncludesCallbackInstructions:
    """
    REQUIREMENT: The enriched prompt includes callback instructions so the LLM
    reports step results back to the orchestrator.

    WHO: The LLM consumer that must know how to report outcomes
    WHAT: The prompt instructs the LLM to call report_step_result; it specifies
          the expected assertion count; it names the output variables to extract
    WHY: Without callback instructions the orchestrator cannot track step
         completion, validate assertions, or propagate variables to later steps

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O for workflow loading)
        Real:  execute_workflow_step, WorkflowState, prompt construction logic
        Never: Construct prompt strings directly — always obtain via execute_workflow_step()
    """

    def test_prompt_instructs_report_step_result(self, loaded_workflow: WorkflowState) -> None:
        """
        When execute_workflow_step is called
        Then the prompt instructs the LLM to call report_step_result
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the prompt contains callback instruction
        prompt = result["prompt"]
        assert "report_step_result" in prompt, (
            f"Expected 'report_step_result' callback instruction in prompt, got: {prompt[:200]}"
        )

    def test_prompt_specifies_expected_assertion_count(
        self, loaded_workflow: WorkflowState
    ) -> None:
        """
        When execute_workflow_step is called for step 1
        Then the prompt specifies the expected number of assertions
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the prompt contains the assertion count (step 1 has 2 assertions)
        prompt = result["prompt"]
        assert "2" in prompt, (
            f"Expected assertion count '2' in prompt (step 1 has 2 assertions), "
            f"got: {prompt[:200]}"
        )

    def test_prompt_specifies_output_variable_names(self, loaded_workflow: WorkflowState) -> None:
        """
        When execute_workflow_step is called for step 1
        Then the prompt names the expected output variables
        """
        # Given: a loaded workflow at step 0 (from loaded_workflow fixture)

        # When: the workflow step is executed
        result = execute_workflow_step()

        # Then: the prompt names the output variable REPO_NAME
        prompt = result["prompt"]
        assert "REPO_NAME" in prompt, (
            f"Expected output variable 'REPO_NAME' in prompt, got: {prompt[:200]}"
        )
