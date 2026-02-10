"""
MCP Server integration specifications

Tests the server's routing layer (call_tool), tool listing,
and error handling at the MCP boundary.
These exercise the public async interface that MCP clients interact with.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workflow_orchestrator_mcp.server import app, call_tool, list_tools, main, run


@pytest.fixture
def valid_workflow_content():
    """Minimal workflow for server integration tests"""
    return """# Server Test Workflow

### 🔧 WORKFLOW STEP: Test step
```
Execute the test tool.
```

### 🛠️ TOOL: test_tool

### ✅ ASSERT:
- result.ok == true
"""


class TestListTools:
    """Server exposes workflow orchestration tools to MCP clients"""

    @pytest.mark.asyncio
    async def test_lists_all_five_tools(self):
        """
        As an MCP client
        I need to discover available workflow tools
        So that I know what capabilities the server offers
        """
        tools = await list_tools()

        tool_names = [t.name for t in tools]
        assert "load_workflow" in tool_names
        assert "execute_workflow_step" in tool_names
        assert "report_step_result" in tool_names
        assert "get_workflow_state" in tool_names
        assert "reset_workflow" in tool_names
        assert len(tools) == 5

    @pytest.mark.asyncio
    async def test_each_tool_has_input_schema(self):
        """
        As an MCP client
        I need each tool to declare its input schema
        So that I can validate arguments before calling
        """
        tools = await list_tools()

        for tool in tools:
            assert tool.inputSchema is not None
            assert "type" in tool.inputSchema


class TestCallToolRouting:
    """Server routes tool calls to the correct workflow function"""

    @pytest.mark.asyncio
    async def test_routes_load_workflow(self, valid_workflow_content):
        """
        As an MCP client
        I need load_workflow routed correctly
        So that workflow files are parsed and loaded
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=valid_workflow_content):
            result = await call_tool("load_workflow", {"file_path": "/test/workflow.md"})

        assert len(result) == 1
        assert "success" in result[0].text.lower() or "step_count" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_routes_execute_workflow_step(self, valid_workflow_content):
        """
        As an MCP client
        I need execute_workflow_step routed correctly
        So that I receive the enriched prompt for the current step
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=valid_workflow_content):
            await call_tool("load_workflow", {"file_path": "/test/workflow.md"})
            result = await call_tool("execute_workflow_step", {})

        assert len(result) == 1
        assert "test_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_routes_report_step_result(self, valid_workflow_content):
        """
        As an MCP client
        I need report_step_result routed correctly
        So that step outcomes are recorded
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=valid_workflow_content):
            await call_tool("load_workflow", {"file_path": "/test/workflow.md"})
            await call_tool("execute_workflow_step", {})
            result = await call_tool("report_step_result", {
                "step_number": 0,
                "status": "passed",
                "assertion_results": [
                    {"assertion": "result.ok == true", "passed": True, "detail": "ok"}
                ],
            })

        assert len(result) == 1
        assert "success" in result[0].text.lower() or "complete" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_routes_get_workflow_state(self, valid_workflow_content):
        """
        As an MCP client
        I need get_workflow_state routed correctly
        So that I can query workflow progress
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=valid_workflow_content):
            await call_tool("load_workflow", {"file_path": "/test/workflow.md"})
            result = await call_tool("get_workflow_state", {})

        assert len(result) == 1
        assert "total_steps" in result[0].text

    @pytest.mark.asyncio
    async def test_routes_reset_workflow(self, valid_workflow_content):
        """
        As an MCP client
        I need reset_workflow routed correctly
        So that I can restart workflow execution
        """
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=valid_workflow_content):
            await call_tool("load_workflow", {"file_path": "/test/workflow.md"})
            result = await call_tool("reset_workflow", {})

        assert len(result) == 1
        assert "success" in result[0].text.lower()


class TestCallToolErrorHandling:
    """Server error handling at the MCP boundary"""

    @pytest.mark.asyncio
    async def test_actionable_error_returns_structured_response(self):
        """
        As an MCP client
        I need ActionableErrors returned as structured text (not exceptions)
        So that the LLM can interpret the error and take corrective action
        """
        # No workflow loaded — should return error response, not raise
        result = await call_tool("get_workflow_state", {})

        assert len(result) == 1
        text = result[0].text.lower()
        assert "success" in text and "false" in text
        assert "error" in text

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_response(self):
        """
        As an MCP client
        I need unknown tool names handled gracefully
        So that the server doesn't crash on bad input
        """
        result = await call_tool("nonexistent_tool", {})

        assert len(result) == 1
        text = result[0].text.lower()
        assert "error" in text
        assert "unexpected" in text

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_error_response(self):
        """
        As an MCP client
        I need unexpected exceptions caught and returned as error text
        So that the server remains stable
        """
        with patch(
            "workflow_orchestrator_mcp.server.load_workflow",
            side_effect=RuntimeError("Something broke"),
        ):
            result = await call_tool("load_workflow", {"file_path": "/test.md"})

        assert len(result) == 1
        text = result[0].text.lower()
        assert "unexpected" in text
        assert "something broke" in text


class TestServerEntryPoints:
    """Server startup infrastructure"""

    @pytest.mark.asyncio
    async def test_main_starts_server_on_stdio(self):
        """
        As a server operator
        I need main() to start the MCP server over stdio
        So that Copilot can communicate with the orchestrator
        """
        mock_read = MagicMock()
        mock_write = MagicMock()

        @asynccontextmanager
        async def fake_stdio_server():
            yield (mock_read, mock_write)

        with patch("workflow_orchestrator_mcp.server.stdio_server", fake_stdio_server), \
             patch.object(app, "run", new_callable=AsyncMock) as mock_run, \
             patch.object(app, "create_initialization_options", return_value={"opts": True}):
            await main()

        mock_run.assert_called_once_with(mock_read, mock_write, {"opts": True})

    def test_run_invokes_main_via_asyncio(self):
        """
        As a server operator
        I need run() to bridge sync→async by calling asyncio.run(main())
        So that the entry point works from a synchronous context
        """
        with patch("workflow_orchestrator_mcp.server.asyncio") as mock_asyncio:
            run()

        mock_asyncio.run.assert_called_once()
        # The argument should be a coroutine (from calling main())
        args = mock_asyncio.run.call_args
        assert args is not None
