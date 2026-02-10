"""
MCP Server for Workflow Orchestrator

Provides tools for orchestrating AI workflows defined in markdown
with natural language, tool specifications, assertions, and variable flow.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .common import ActionableError
from .tools.workflow_tools import (
    execute_workflow_step,
    get_workflow_state,
    load_workflow,
    report_step_result,
    reset_workflow,
)

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
