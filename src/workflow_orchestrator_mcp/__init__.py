"""
Workflow Orchestrator MCP Server

An MCP server for orchestrating AI workflows defined in markdown with natural language.
Extends the demo-assistant-mcp pattern with tool specifications, assertions,
variable flow, and a feedback loop via report_step_result.
"""

from .common import ActionableError
from .common.workflow_state import (
    AssertionResult,
    StepOutcome,
    StepStatus,
    WorkflowState,
    WorkflowStep,
    get_state,
    require_loaded_workflow,
)
from .tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
    reset_workflow,
)

__version__ = "0.1.0"

__all__ = [
    "ActionableError",
    "WorkflowStep",
    "WorkflowState",
    "StepOutcome",
    "StepStatus",
    "AssertionResult",
    "load_workflow",
    "execute_workflow_step",
    "report_step_result",
    "get_workflow_state",
    "reset_workflow",
    "get_state",
    "require_loaded_workflow",
]
