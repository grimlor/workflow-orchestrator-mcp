"""
Complete workflow execution specifications

Covers end-to-end workflow orchestration through the public API:
load_workflow → (execute_workflow_step → report_step_result)* → get_workflow_state

Spec classes:
    TestExecuteCompleteWorkflowSuccessfully
    TestWorkflowExecutionWithStepFailure
    TestWorkflowStateTracking
    TestResumeWorkflowFromFailurePoint
"""

from __future__ import annotations

from typing import Any

from workflow_orchestrator_mcp.common.workflow_state import StepStatus, WorkflowState, get_state
from workflow_orchestrator_mcp.tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
    reset_workflow,
)


def _execute_and_report(
    state: WorkflowState,
    step_idx: int,
    status: str = "passed",
    outputs: dict[str, str] | None = None,
) -> None:
    """Helper: execute a step and report its result via public API"""
    execute_workflow_step()
    assertions = state.steps[step_idx].assertions
    report_step_result(
        step_number=step_idx,
        status=status,
        assertion_results=[
            {
                "assertion": a,
                "passed": status == "passed",
                "detail": "ok" if status == "passed" else "failed",
            }
            for a in assertions
        ],
        output_variables=outputs or {},
        error_message="" if status == "passed" else "Step failed",
    )


class TestExecuteCompleteWorkflowSuccessfully:
    """
    REQUIREMENT: A workflow with all steps passing completes successfully.

    WHO: The workflow author running an end-to-end workflow
    WHAT: All steps execute in order and pass; output variables are
          accumulated across steps and available in final state
    WHY: The orchestrator must prove that the happy-path execution
         collects all artifacts and reaches a completed state

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, workflow_tools functions, step execution logic
        Never: Construct WorkflowState directly — always obtain via get_state()
    """

    def test_all_steps_pass_in_order(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a 3-step workflow loaded from disk
        When all steps are executed and reported as passed
        Then the workflow state is complete with no failures
        """
        # Given: a workflow loaded from the mock filesystem
        load_workflow("/path/to/workflow.md")
        state = get_state()

        # When: all 3 steps are executed and reported as passed
        _execute_and_report(state, 0, outputs={"REPO_NAME": "my-repo"})
        _execute_and_report(state, 1)
        _execute_and_report(state, 2, outputs={"PR_ID": "42"})

        # Then: the workflow is complete with no failures
        assert state.is_complete is True, (
            f"Expected workflow to be complete after all steps passed, "
            f"got is_complete={state.is_complete}"
        )
        assert state.is_failed is False, (
            f"Expected workflow not to be failed, got is_failed={state.is_failed}"
        )
        assert len(state.completed_steps) == 3, (
            f"Expected 3 completed steps, got {len(state.completed_steps)}: "
            f"{state.completed_steps}"
        )

    def test_all_variables_collected(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a 3-step workflow where steps 1 and 3 produce output variables
        When all steps pass
        Then the final state contains all output variables from all steps
        """
        # Given: a workflow loaded from the mock filesystem
        load_workflow("/path/to/workflow.md")
        state = get_state()

        # When: all steps are executed with output variables on steps 1 and 3
        _execute_and_report(state, 0, outputs={"REPO_NAME": "my-repo"})
        _execute_and_report(state, 1)
        _execute_and_report(state, 2, outputs={"PR_ID": "99"})

        # Then: all variables are present in the workflow state
        assert state.variables["REPO_NAME"] == "my-repo", (
            f"Expected REPO_NAME='my-repo', got '{state.variables.get('REPO_NAME')}'"
        )
        assert state.variables["PR_ID"] == "99", (
            f"Expected PR_ID='99', got '{state.variables.get('PR_ID')}'"
        )


class TestWorkflowExecutionWithStepFailure:
    """
    REQUIREMENT: A step failure halts execution and marks the workflow as failed.

    WHO: The workflow author diagnosing a broken run
    WHAT: When a step fails, preceding steps retain their passed status,
          the failed step is marked as failed, and the workflow is_failed
    WHY: The author must see exactly which step broke to know where to
         investigate — conflating passed and failed steps hides the root cause

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, workflow_tools functions, step outcome tracking
        Never: Construct StepOutcome directly — always obtain via report_step_result
    """

    def test_failure_at_step2_shows_correct_statuses(
        self, mock_file_system: tuple[Any, Any]
    ) -> None:
        """
        Given a 3-step workflow where step 1 passes and step 2 fails
        When the step outcomes are inspected
        Then step 1 shows passed, step 2 shows failed, and is_failed is True
        """
        # Given: a loaded workflow
        load_workflow("/path/to/workflow.md")
        state = get_state()

        # When: step 1 passes and step 2 fails
        _execute_and_report(state, 0, outputs={"REPO_NAME": "my-repo"})
        _execute_and_report(state, 1, status="failed")

        # Then: statuses reflect the pass/fail correctly
        assert state.step_outcomes[0].status == StepStatus.PASSED, (
            f"Expected step 0 status PASSED, got {state.step_outcomes[0].status}"
        )
        assert state.step_outcomes[1].status == StepStatus.FAILED, (
            f"Expected step 1 status FAILED, got {state.step_outcomes[1].status}"
        )
        assert state.is_failed is True, (
            f"Expected workflow is_failed=True after step failure, got {state.is_failed}"
        )


class TestWorkflowStateTracking:
    """
    REQUIREMENT: Workflow state is queryable at any point during execution.

    WHO: The workflow author monitoring progress mid-run
    WHAT: The state dict reports total steps, current step index,
          completed step indices, and completion status at any point
    WHY: Without mid-execution visibility the author cannot tell whether
         the workflow is progressing or stuck

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, get_workflow_state() public API
        Never: Read internal state fields directly — always use get_workflow_state()
    """

    def test_query_state_during_execution(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a 3-step workflow with step 1 completed
        When the state is queried via the public API
        Then it shows 3 total steps, current step 1, and step 0 completed
        """
        # Given: a workflow with step 1 completed
        load_workflow("/path/to/workflow.md")
        state = get_state()
        _execute_and_report(state, 0, outputs={"REPO_NAME": "my-repo"})

        # When: state is queried via public API
        state_dict = get_workflow_state()

        # Then: progress is accurately reflected
        assert state_dict["total_steps"] == 3, (
            f"Expected total_steps=3, got {state_dict['total_steps']}"
        )
        assert state_dict["current_step"] == 1, (
            f"Expected current_step=1, got {state_dict['current_step']}"
        )
        assert 0 in state_dict["completed_steps"], (
            f"Expected step 0 in completed_steps, got {state_dict['completed_steps']}"
        )
        assert state_dict["is_complete"] is False, (
            f"Expected is_complete=False with 1 of 3 steps done, got {state_dict['is_complete']}"
        )

    def test_state_shows_current_step(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        When a workflow is freshly loaded
        Then the state shows current step 0 and the correct total step count
        """
        # Given: a freshly loaded workflow
        load_workflow("/path/to/workflow.md")

        # When: state is queried
        state_dict = get_workflow_state()

        # Then: current step is 0, total steps is 3
        assert state_dict["current_step"] == 0, (
            f"Expected current_step=0 for fresh workflow, got {state_dict['current_step']}"
        )
        assert state_dict["total_steps"] == 3, (
            f"Expected total_steps=3, got {state_dict['total_steps']}"
        )


class TestResumeWorkflowFromFailurePoint:
    """
    REQUIREMENT: A workflow can be reset and re-executed from the beginning.

    WHO: The workflow author retrying after fixing an issue
    WHAT: After reset, the workflow state is clean — current step is 0,
          no outcomes exist, and is_failed is False
    WHY: Without a clean reset, stale outcomes from the previous run
         would corrupt the retry attempt

    MOCK BOUNDARY:
        Mock:  filesystem via mock_file_system fixture (pathlib.Path I/O)
        Real:  WorkflowState, reset_workflow(), step execution logic
        Never: Mutate workflow state fields directly — always use reset_workflow()

    MVP scope: Resume is within a single MCP server session only.
    State is in-memory; restarting the server process loses workflow state.
    """

    def test_resume_skips_completed_steps(self, mock_file_system: tuple[Any, Any]) -> None:
        """
        Given a workflow where steps 1-2 passed and step 3 failed
        When the workflow is reset
        Then the state is clean for a fresh run
        """
        # Given: a workflow where steps 1-2 passed and step 3 failed
        load_workflow("/path/to/workflow.md")
        state = get_state()
        _execute_and_report(state, 0, outputs={"REPO_NAME": "my-repo"})
        _execute_and_report(state, 1)
        _execute_and_report(state, 2, status="failed")

        # When: the workflow is reset
        reset_workflow()

        # Then: state is clean for a fresh run
        state = get_state()
        assert state.current_step == 0, (
            f"Expected current_step=0 after reset, got {state.current_step}"
        )
        assert len(state.step_outcomes) == 0, (
            f"Expected no step_outcomes after reset, got {len(state.step_outcomes)}"
        )
        assert state.is_failed is False, (
            f"Expected is_failed=False after reset, got {state.is_failed}"
        )
