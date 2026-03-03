"""
Workflow Orchestrator MCP Server

An MCP server for orchestrating AI workflows defined in markdown with natural language.
Extends the demo-assistant-mcp pattern with tool specifications, assertions,
variable flow, and a feedback loop via report_step_result.
"""

from __future__ import annotations

from .common import ActionableError, WorkflowError, WorkflowErrorType
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
    "AssertionResult",
    "StepOutcome",
    "StepStatus",
    "WorkflowError",
    "WorkflowErrorType",
    "WorkflowState",
    "WorkflowStep",
    "execute_workflow_step",
    "get_state",
    "get_workflow_state",
    "get_workflow_template",
    "load_workflow",
    "report_step_result",
    "require_loaded_workflow",
    "reset_workflow",
]
