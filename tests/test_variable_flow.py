"""
Scenario Group 4: Variable Flow Between Steps

Tests the public APIs: report_step_result() (output capture) and
execute_workflow_step() (variable substitution in prompts).
"""


import pytest

from workflow_orchestrator_mcp.common.error_handling import ActionableError
from workflow_orchestrator_mcp.common.workflow_state import get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    load_workflow,
    report_step_result,
)


@pytest.fixture
def loaded_workflow(mock_file_system):
    """Load a valid workflow for variable flow tests"""
    load_workflow("/path/to/workflow.md")
    return get_state()


def _advance_step(state, step_number, outputs=None):
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
    """Scenario 4.1: LLM reports output variables via callback"""

    def test_output_variable_stored_in_state(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need output variables from the LLM stored in state
        So that subsequent steps can use them
        """
        execute_workflow_step()
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[
                {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
            ],
            output_variables={"REPO_NAME": "my-awesome-repo"},
        )

        state = get_state()
        assert "REPO_NAME" in state.variables
        assert state.variables["REPO_NAME"] == "my-awesome-repo"


class TestSubstituteVariableInNextStep:
    """Scenario 4.2: Substitute variable in next step's enriched prompt"""

    def test_repo_name_substituted_in_step2_prompt(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need variables from step 1 substituted into step 2's prompt
        So that the LLM works with concrete values, not placeholders
        """
        # Complete step 1, producing REPO_NAME
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "my-repo"})

        # Now step 2's prompt should have REPO_NAME resolved
        result = execute_workflow_step()

        prompt = result["prompt"]
        assert "my-repo" in prompt
        assert "[REPO_NAME]" not in prompt


class TestVariableSubstitutionInDescription:
    """Scenario 4.3: Variable substitution in step description"""

    def test_description_shows_substituted_value(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need [VARIABLE_NAME] in descriptions replaced with actual values
        So that the LLM sees the concrete context
        """
        # Step 2 description contains "[REPO_NAME]"
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "test-repo"})

        result = execute_workflow_step()

        prompt = result["prompt"]
        assert "test-repo" in prompt


class TestMissingRequiredInputVariable:
    """Scenario 4.4: Missing required input variable"""

    def test_raises_error_when_input_variable_missing(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need an error when a required input variable isn't available
        So that the workflow fails clearly instead of using stale/empty data
        """
        # Complete step 1 WITHOUT producing REPO_NAME
        execute_workflow_step()

        # report_step_result auto-builds next step prompt, which triggers missing var
        with pytest.raises(ActionableError) as exc_info:
            report_step_result(
                step_number=0,
                status="passed",
                assertion_results=[
                    {"assertion": 'result contains "repositories"', "passed": True, "detail": ""},
                    {"assertion": "result.repositories.length > 0", "passed": True, "detail": ""},
                ],
                output_variables={},  # No REPO_NAME!
            )

        assert "REPO_NAME" in str(exc_info.value)


class TestChainOutputsThroughMultipleSteps:
    """Scenario 4.5: Chain outputs through multiple steps"""

    def test_variables_flow_through_chain(self, loaded_workflow):
        """
        As a workflow orchestrator
        I need variables to chain through step 1 → step 2 → step 3
        So that each step builds on previous results
        """
        # Step 1 → produces REPO_NAME
        _advance_step(loaded_workflow, 0, outputs={"REPO_NAME": "chained-repo"})

        # Step 2 → uses REPO_NAME, produces nothing new for this test
        _advance_step(loaded_workflow, 1, outputs={})

        # Step 3 → should still have REPO_NAME available, and produce PR_ID
        result = execute_workflow_step()
        # Step 3's prompt should be buildable (no missing variable errors)
        assert "prompt" in result

        # Complete step 3 → produces PR_ID
        report_step_result(
            step_number=2,
            status="passed",
            assertion_results=[
                {"assertion": 'result.status == "active"', "passed": True, "detail": ""},
                {"assertion": "result.pullRequestId > 0", "passed": True, "detail": ""},
            ],
            output_variables={"PR_ID": "42"},
        )

        state = get_state()
        assert state.variables["REPO_NAME"] == "chained-repo"
        assert state.variables["PR_ID"] == "42"
