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
    get_workflow_template,
    load_workflow,
    report_step_result,
    reset_workflow,
)

try:
    from ._version import __version__
except ImportError:  # editable install or no build
    __version__ = "0.0.0+unknown"

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
    "get_workflow_template",
    "reset_workflow",
    "get_state",
    "require_loaded_workflow",
]
