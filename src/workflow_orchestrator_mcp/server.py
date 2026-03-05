"""
Workflow Orchestrator MCP Server

FastMCP-based server that exposes workflow orchestration tools and
a docs resource over the MCP protocol (stdio transport).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from actionable_errors import ToolResult
from fastmcp import FastMCP

from .common import ActionableError
from .tools import workflow_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP("workflow-orchestrator-mcp")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def load_workflow(file_path: str) -> str:
    """Load and parse a workflow markdown file.

    Args:
        file_path: Path to the workflow markdown file.
    """
    try:
        result = workflow_tools.load_workflow(file_path)
        return str(result)
    except ActionableError as e:
        logger.warning("load_workflow failed: %s", e)
        return str(ToolResult.fail(e).to_dict())


@mcp.tool()
async def execute_workflow_step() -> str:
    """Build and return the enriched prompt for the current workflow step."""
    try:
        result = workflow_tools.execute_workflow_step()
        return str(result)
    except ActionableError as e:
        logger.warning("execute_workflow_step failed: %s", e)
        return str(ToolResult.fail(e).to_dict())


@mcp.tool()
async def report_step_result(
    step_number: int,
    status: str,
    assertion_results: list[dict[str, Any]] | None = None,
    output_variables: dict[str, Any] | None = None,
    error_message: str = "",
) -> str:
    """Report execution results for a workflow step.

    Args:
        step_number: The step number being reported on.
        status: "passed" or "failed".
        assertion_results: Per-assertion pass/fail results.
        output_variables: Extracted output variable values.
        error_message: Error details if the step failed.
    """
    try:
        result = workflow_tools.report_step_result(
            step_number=step_number,
            status=status,
            assertion_results=assertion_results,
            output_variables=output_variables,
            error_message=error_message,
        )
        return str(result)
    except ActionableError as e:
        logger.warning("report_step_result failed: %s", e)
        return str(ToolResult.fail(e).to_dict())


@mcp.tool()
async def get_workflow_state() -> str:
    """Get the current state of the loaded workflow."""
    try:
        result = workflow_tools.get_workflow_state()
        return str(result)
    except ActionableError as e:
        logger.warning("get_workflow_state failed: %s", e)
        return str(ToolResult.fail(e).to_dict())


@mcp.tool()
async def reset_workflow() -> str:
    """Reset the workflow to its beginning state."""
    try:
        result = workflow_tools.reset_workflow()
        return str(result)
    except ActionableError as e:
        logger.warning("reset_workflow failed: %s", e)
        return str(ToolResult.fail(e).to_dict())


@mcp.tool()
async def get_workflow_template(task_description: str | None = None) -> str:
    """Return the workflow format spec, skeleton, and concrete example.

    Args:
        task_description: Optional brief description of what the workflow
            should accomplish. Included in the response when provided.
    """
    template_path = Path(__file__).resolve().parent / "resources" / "workflow_template.md"
    result = workflow_tools.get_workflow_template(
        template_path=template_path,
        task_description=task_description,
    )
    return str(result)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("workflow://docs")
def get_docs_link() -> str:
    """Return the GitHub docs URL for the workflow orchestrator."""
    return "https://github.com/grimlor/workflow-orchestrator-mcp/tree/main/docs"


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def run() -> None:
    """Synchronous entry point (used by pyproject.toml [project.scripts])."""
    mcp.run(transport="stdio")


async def main() -> None:
    """Async entry point for programmatic use."""
    await mcp.run_async(transport="stdio")
