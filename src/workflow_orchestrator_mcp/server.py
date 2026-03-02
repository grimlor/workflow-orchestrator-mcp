"""
MCP Server for Workflow Orchestrator

Provides tools for orchestrating AI workflows defined in markdown
with natural language, tool specifications, assertions, and variable flow.

Also exposes MCP resources so that agents can browse the workflow-format
specification, a starter template, and example workflows.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl

from .common import ActionableError
from .tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    get_workflow_template,
    load_workflow,
    report_step_result,
    reset_workflow,
)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_PACKAGE_ROOT = Path(__file__).resolve().parent
# Template ships inside the package so it survives pip/uvx install
_WORKFLOW_TEMPLATE_PATH = _PACKAGE_ROOT / "resources" / "workflow_template.md"
# Docs and demos are repo-level only (not in the wheel)
_DOCS_DIR = _PACKAGE_ROOT.parent.parent / "docs"
_WORKFLOW_FORMAT_PATH = _DOCS_DIR / "WORKFLOW_FORMAT.md"
_DEMO_DIR = _DOCS_DIR / "demo workflows"

# Set up logging
logger = logging.getLogger("workflow-orchestrator-mcp")
logger.setLevel(logging.INFO)

# Create server instance
app = Server("workflow-orchestrator-mcp")


# Tool definitions for MCP
TOOLS = [
    Tool(
        name="load_workflow",
        description=(
            "Load and parse a workflow markdown file. "
            "Extracts steps tagged with '### 🔧 WORKFLOW STEP:' including tool specifications, "
            "inputs, outputs, and assertions. "
            "Returns step count and the first step's enriched prompt for execution."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the workflow markdown file"
                }
            },
            "required": ["file_path"]
        }
    ),
    Tool(
        name="execute_workflow_step",
        description=(
            "Execute the current workflow step by returning an enriched prompt. "
            "The prompt includes the step description, tool names, resolved variables, "
            "assertion criteria, and instructions to call report_step_result when done. "
            "The LLM should execute the prompt, evaluate assertions, and report back."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="report_step_result",
        description=(
            "Callback tool: report the outcome of a workflow step after execution. "
            "The LLM calls this after executing a step to report pass/fail status, "
            "assertion results, and any output variables extracted from the results. "
            "The orchestrator records the outcome and returns the next step or completion status."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "step_number": {
                    "type": "integer",
                    "description": "The step number being reported on"
                },
                "status": {
                    "type": "string",
                    "enum": ["passed", "failed"],
                    "description": "Whether the step passed or failed"
                },
                "assertion_results": {
                    "type": "array",
                    "description": "Per-assertion pass/fail results",
                    "items": {
                        "type": "object",
                        "properties": {
                            "assertion": {
                                "type": "string",
                                "description": "The original assertion text"
                            },
                            "passed": {
                                "type": "boolean",
                                "description": "Whether this assertion passed"
                            },
                            "detail": {
                                "type": "string",
                                "description": "Explanation of the result"
                            }
                        },
                        "required": ["assertion", "passed"]
                    }
                },
                "output_variables": {
                    "type": "object",
                    "description": "Output variables extracted from results (variable name → value)",
                    "additionalProperties": True
                },
                "error_message": {
                    "type": "string",
                    "description": "Error details if the step failed"
                }
            },
            "required": ["step_number", "status"]
        }
    ),
    Tool(
        name="get_workflow_state",
        description=(
            "Get the current state of the loaded workflow. "
            "Returns progress information including which steps have passed, failed, "
            "or are pending, current variables, and assertion results."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="reset_workflow",
        description=(
            "Reset the workflow to the beginning. "
            "Clears all step outcomes, variables, and execution state. "
            "The workflow script remains loaded."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="get_workflow_template",
        description=(
            "Get the workflow-format specification, a starter skeleton, and a "
            "concrete example so you can author a new orchestration workflow. "
            "Call this tool whenever you need to create or understand a workflow "
            "markdown file. Optionally provide a task_description to include "
            "context about what the workflow should accomplish."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": (
                        "Optional brief description of what the workflow should "
                        "accomplish. When provided, it is included in the response "
                        "so you can tailor the template to the task."
                    )
                }
            },
            "required": []
        }
    ),
]


@app.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[Tool]:
    """List available workflow orchestration tools"""
    return TOOLS


@app.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls from the MCP client.

    Routes to appropriate workflow tool function and handles errors.
    """
    try:
        logger.info(f"Tool called: {name} with arguments: {arguments}")

        if name == "load_workflow":
            result = load_workflow(arguments["file_path"])
        elif name == "execute_workflow_step":
            result = execute_workflow_step()
        elif name == "report_step_result":
            result = report_step_result(
                step_number=arguments["step_number"],
                status=arguments["status"],
                assertion_results=arguments.get("assertion_results", []),
                output_variables=arguments.get("output_variables", {}),
                error_message=arguments.get("error_message", ""),
            )
        elif name == "get_workflow_state":
            result = get_workflow_state()
        elif name == "reset_workflow":
            result = reset_workflow()
        elif name == "get_workflow_template":
            result = get_workflow_template(
                template_path=_WORKFLOW_TEMPLATE_PATH,
                task_description=arguments.get("task_description"),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        logger.info(f"Tool {name} succeeded")
        return [TextContent(type="text", text=str(result))]

    except ActionableError as e:
        # Return actionable errors as structured text
        logger.warning(f"Tool {name} failed with ActionableError: {e}")
        error_response = {
            "success": False,
            "error": str(e),
            "error_type": e.error_type.value,
        }
        return [TextContent(type="text", text=str(error_response))]

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Tool {name} failed with unexpected error: {e}", exc_info=True)
        error_response = {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected",
        }
        return [TextContent(type="text", text=str(error_response))]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_docs_file(path: Path) -> str:
    """Read a docs file from disk. Raises FileNotFoundError if missing."""
    return path.read_text(encoding="utf-8")


def _discover_demo_workflows() -> dict[str, Path]:
    """Return {stem: path} for every .md file in the demo workflows dir."""
    if _DEMO_DIR.is_dir():
        return {p.stem: p for p in sorted(_DEMO_DIR.glob("*.md"))}
    return {}


# ---------------------------------------------------------------------------
# MCP Resources – expose repo-level docs and demo workflows for browsing
# (These are available in repo-checkout mode only; after pip/uvx install the
# template is still accessible via the get_workflow_template tool.)
# ---------------------------------------------------------------------------

@app.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_resources() -> list[Resource]:
    """List docs and demo workflow files as resources (repo-checkout only)."""
    resources: list[Resource] = []

    # Format spec (repo-level docs)
    if _WORKFLOW_FORMAT_PATH.is_file():
        resources.append(
            Resource(
                uri=AnyUrl("workflow://docs/WORKFLOW_FORMAT.md"),
                name="Workflow Format Specification",
                description="Complete specification for authoring orchestration workflows",
                mimeType="text/markdown",
            )
        )

    # Demo workflows discovered on disk
    for stem, _path in _discover_demo_workflows().items():
        resources.append(
            Resource(
                uri=AnyUrl(f"workflow://demos/{stem}.md"),
                name=stem.replace("_", " ").title(),
                description=f"Demo workflow: {stem.replace('_', ' ')}",
                mimeType="text/markdown",
            )
        )

    return resources


@app.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
async def read_resource(uri: str) -> str:
    """Return the content of a workflow doc or demo file."""
    uri_str = str(uri)

    if uri_str == "workflow://docs/WORKFLOW_FORMAT.md":
        return _read_docs_file(_WORKFLOW_FORMAT_PATH)

    if uri_str.startswith("workflow://demos/"):
        filename = uri_str.removeprefix("workflow://demos/")
        stem = filename.removesuffix(".md")
        demos = _discover_demo_workflows()
        if stem in demos:
            return demos[stem].read_text(encoding="utf-8")
        raise ValueError(f"Demo workflow not found: {filename}")

    raise ValueError(f"Unknown resource URI: {uri_str}")


async def main() -> None:
    """Run the MCP server via stdio"""
    logger.info("Starting workflow-orchestrator-mcp server")

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def run() -> None:
    """Entry point for the server"""
    asyncio.run(main())


if __name__ == "__main__":  # pragma: no cover
    run()
