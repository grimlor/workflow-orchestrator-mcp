"""
Scenario Group 4: Variable Flow Between Steps

Tests the public APIs: report_step_result() (output capture) and
execute_workflow_step() (variable substitution in prompts).
"""

from __future__ import annotations

from typing import Any

import pytest

from workflow_orchestrator_mcp.common.errors import WorkflowError
from workflow_orchestrator_mcp.common.workflow_state import WorkflowState, get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def loaded_workflow(mock_file_system: tuple[Any, Any]) -> WorkflowState:
    """Load a valid workflow for variable flow tests"""
    load_workflow("/path/to/workflow.md")
    return get_state()


def _advance_step(
    state: WorkflowState, step_number: int, outputs: dict[str, str] | None = None
) -> None:
    """Helper: simulate executing and reporting a step via public API"""
    execute_workflow_step()
    report_step_result(
        step_number=step_number,
        status="passed",
        assertion_results=[
            {"assertion": a, "passed": True, "detail": "ok"}
            for a in state.steps[step_number].assertions
        ],
        output_variables=outputs or {},
    )


class TestLLMReportsOutputVariables:
    """
    REQUIREMENT: Output variables reported by the LLM are persisted in workflow state.

    WHO: The workflow orchestrator storing step outputs for downstream consumption
    WHAT: When report_step_result includes output_variables, those variables
          appear in WorkflowState.variables with the reported values
    WHY: Subsequent steps depend on earlier outputs; if variables are not
         persisted, downstream substitution silently produces empty prompts

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, report_step_result, execute_workflow_step
        Never: Mutate state.variables directly — always go through report_step_result
    """

    def test_output_variable_stored_in_state(self, loaded_workflow: WorkflowState) -> None:
        """
        When report_step_result is called with an output variable
        Then the variable is stored in workflow state with the reported value
        """
        # Given: step 0 has been executed
        execute_workflow_step()

        # When: the step result is reported with an output variable
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "my-awesome-repo"},
        )

        # Then: the variable is persisted in state
        state = get_state()
        assert "REPO_NAME" in state.variables, (
            f"Expected REPO_NAME in state.variables, got keys: {list(state.variables.keys())}"
        )
        assert state.variables["REPO_NAME"] == "my-awesome-repo", (
            f"Expected REPO_NAME='my-awesome-repo', got '{state.variables.get('REPO_NAME')}'"
        )


class TestSubstituteVariableInNextStep:
    """
    REQUIREMENT: Variables from earlier steps are substituted into subsequent step prompts.

    WHO: The prompt builder resolving placeholders before sending to the LLM
    WHAT: When step 1 produces REPO_NAME, step 2's enriched prompt contains
          the concrete value and no longer contains the [REPO_NAME] placeholder
    WHY: The LLM must receive concrete values, not variable placeholders,
         to produce meaningful tool calls and responses

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, execute_workflow_step, report_step_result
        Never: Construct prompt strings directly — always obtain via execute_workflow_step
    """

    def test_repo_name_substituted_in_step2_prompt(self, loaded_workflow: WorkflowState) -> None:
        """
        Given step 1 has been completed with REPO_NAME output
        When step 2's prompt is built via execute_workflow_step
        Then the prompt contains the concrete value and no placeholder
        """
        # Given: step 1 completed, producing REPO_NAME
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "my-repo"})

        # When: step 2's prompt is built
        result = execute_workflow_step()

        # Then: the prompt contains the substituted value, not the placeholder
        prompt = result["prompt"]
        assert "my-repo" in prompt, (
            f"Expected 'my-repo' in prompt, got: {prompt[:200]}"
        )
        assert "[REPO_NAME]" not in prompt, (
            f"Placeholder [REPO_NAME] should be resolved but still present in: {prompt[:200]}"
        )


class TestVariableSubstitutionInDescription:
    """
    REQUIREMENT: Variable placeholders in step descriptions are replaced with actual values.

    WHO: The prompt builder rendering step descriptions for the LLM
    WHAT: When a step description contains [REPO_NAME] and the variable
          has been set by a prior step, the enriched prompt shows the
          concrete value instead of the placeholder
    WHY: Unresolved placeholders in descriptions confuse the LLM and
         produce incorrect tool calls against literal bracket strings

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, execute_workflow_step, report_step_result
        Never: Construct prompt strings directly — always obtain via execute_workflow_step
    """

    def test_description_shows_substituted_value(self, loaded_workflow: WorkflowState) -> None:
        """
        Given step 1 has been completed with REPO_NAME output
        When step 2's prompt is built (its description contains [REPO_NAME])
        Then the prompt contains the concrete value
        """
        # Given: step 1 completed, producing REPO_NAME
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "test-repo"})

        # When: step 2's prompt is built
        result = execute_workflow_step()

        # Then: the description shows the substituted value
        prompt = result["prompt"]
        assert "test-repo" in prompt, (
            f"Expected 'test-repo' in prompt after substitution, got: {prompt[:200]}"
        )


class TestMissingRequiredInputVariable:
    """
    REQUIREMENT: Missing required input variables produce a clear error.

    WHO: The workflow orchestrator validating variable availability before prompt build
    WHAT: When a step requires [REPO_NAME] but it was never produced by a prior
          step, report_step_result raises a WorkflowError that names the
          missing variable
    WHY: Silent substitution of empty values produces broken prompts;
         an explicit error lets the workflow author fix the dependency chain

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, execute_workflow_step, report_step_result
        Never: Bypass variable validation by mutating state directly
    """

    def test_raises_error_when_input_variable_missing(
        self, loaded_workflow: WorkflowState
    ) -> None:
        """
        Given step 1 completes without producing REPO_NAME
        When report_step_result triggers the next step's prompt build
        Then a WorkflowError is raised that names the missing variable
        """
        # Given: step 1 executed but does not produce REPO_NAME
        execute_workflow_step()

        # When: report_step_result triggers prompt build for next step
        with pytest.raises(WorkflowError) as exc_info:
            report_step_result(
                step_number=0,
                status="passed",
                assertion_results=[
                    {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                    {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
                ],
                output_variables={},  # No REPO_NAME!
            )

        # Then: the error names the missing variable
        assert "REPO_NAME" in str(exc_info.value), (
            f"Error should name the missing variable REPO_NAME. Got: {exc_info.value}"
        )


class TestChainOutputsThroughMultipleSteps:
    """
    REQUIREMENT: Variables chain through multiple sequential steps.

    WHO: The workflow orchestrator accumulating variables across the full pipeline
    WHAT: A variable produced in step 1 remains available through step 2 and
          step 3; each step can add new variables without losing earlier ones
    WHY: Multi-step workflows depend on cumulative context; if earlier
         variables are lost, downstream steps cannot reference prior results

    MOCK BOUNDARY:
        Mock:  mock_file_system fixture (filesystem I/O)
        Real:  WorkflowState, execute_workflow_step, report_step_result
        Never: Mutate state.variables directly — always go through report_step_result
    """

    def test_variables_flow_through_chain(self, loaded_workflow: WorkflowState) -> None:
        """
        Given step 1 produces REPO_NAME and step 2 completes without new outputs
        When step 3 executes and produces PR_ID
        Then both REPO_NAME and PR_ID are present in state variables
        """
        # Given: step 1 produces REPO_NAME, step 2 passes through
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "chained-repo"})
        _advance_step(loaded_workflow, 1, outputs={})

        # When: step 3 executes and produces PR_ID
        result = execute_workflow_step()
        assert "prompt" in result, (
            f"Step 3 prompt should be buildable (no missing variable errors). "
            f"Got keys: {list(result.keys())}"
        )

        report_step_result(
            step_number=2,
            status="passed",
            assertion_results=[
                {"assertion": 'result.status == "active"', "passed": True, "detail": ""},
                {"assertion": "result.pullRequestId > 0", "passed": True, "detail": ""},
            ],
            output_variables={"PR_ID": "42"},
        )

        # Then: both variables are present in state
        state = get_state()
        assert state.variables["REPO_NAME"] == "chained-repo", (
            f"Expected REPO_NAME='chained-repo', got '{state.variables.get('REPO_NAME')}'"
        )
        assert state.variables["PR_ID"] == "42", (
            f"Expected PR_ID='42', got '{state.variables.get('PR_ID')}'"
        )
