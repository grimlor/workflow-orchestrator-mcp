"""
FastMCP server behavior specifications

Tests that the server module exposes correctly-typed tool functions,
handles errors gracefully, provides a docs resource, and has proper
entry points. FastMCP's internal decorator machinery and routing is
NOT tested here — that's FastMCP's CI responsibility.

BDD spec classes:
- TestToolRegistration: Function existence and signature checks
- TestToolExecution: End-to-end tool function calls with real inputs
- TestErrorHandling: Structured error responses from real bad inputs
- TestDocsResource: Static docs link function
- TestServerEntry: run() and main() entry points
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import pytest

from workflow_orchestrator_mcp import server

# Public API surface (from server.py — post-migration):
#   mcp: FastMCP("workflow-orchestrator-mcp") instance
#   load_workflow(file_path: str) -> str
#   execute_workflow_step() -> str
#   report_step_result(step_number: int, status: str, ...) -> str
#   get_workflow_state() -> str
#   reset_workflow() -> str
#   get_workflow_template(task_description: str | None = None) -> str
#   get_docs_link() -> str
#   run() -> None
#   main() -> coroutine

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


class TestToolRegistration:
    """
    REQUIREMENT: Each workflow tool function must exist in server.py
    with the correct signature so that FastMCP can auto-generate schemas.

    WHO: MCP clients (Copilot, Claude, etc.) that call tools/list
    WHAT: Six tool functions exist with typed signatures that match the
          current API — we verify our functions have the right names,
          parameter names, types, and defaults
    WHY: If our function signatures are wrong, FastMCP will generate
         incorrect schemas and clients will send malformed arguments

    MOCK BOUNDARY:
        Mock:  Nothing — these are pure signature/existence checks
        Real:  The tool functions themselves (imported from server module)
        Never: FastMCP internals (we don't test their decorator machinery)
    """

    EXPECTED_TOOLS: ClassVar[list[str]] = [
        "load_workflow",
        "execute_workflow_step",
        "report_step_result",
        "get_workflow_state",
        "reset_workflow",
        "get_workflow_template",
    ]

    def test_six_async_tool_functions_exist(self) -> None:
        """
        Given the server module
        When inspecting exported tool functions
        Then six async functions exist with the expected names
        """
        # Given: the server module
        # When / Then: each function exists and is async
        for name in self.EXPECTED_TOOLS:
            fn = getattr(server, name, None)
            assert fn is not None, f"server module missing tool function: {name}"
            assert callable(fn), f"server.{name} is not callable"
            assert inspect.iscoroutinefunction(fn), (
                f"server.{name} should be an async function, got {type(fn).__name__}"
            )

    def test_load_workflow_requires_file_path_str(self) -> None:
        """
        Given the server module
        When inspecting load_workflow's signature
        Then it requires file_path: str
        """
        # Given: the server module
        fn = getattr(server, "load_workflow", None)
        assert fn is not None, "server.load_workflow not found"

        # When: inspecting signature
        sig = inspect.signature(fn)

        # Then: file_path is required and typed as str
        assert "file_path" in sig.parameters, (
            f"load_workflow missing 'file_path' param. Params: {list(sig.parameters.keys())}"
        )
        param = sig.parameters["file_path"]
        assert param.annotation in (str, "str"), (
            f"file_path should be annotated as str, got {param.annotation}"
        )
        assert param.default is inspect.Parameter.empty, (
            "file_path should be required (no default)"
        )

    def test_report_step_result_has_required_and_optional_params(self) -> None:
        """
        Given the server module
        When inspecting report_step_result's signature
        Then it requires step_number: int and status: str with three
        optional params (assertion_results, output_variables, error_message)
        """
        # Given: the server module
        fn = getattr(server, "report_step_result", None)
        assert fn is not None, "server.report_step_result not found"

        # When: inspecting signature
        sig = inspect.signature(fn)
        params = sig.parameters

        # Then: step_number and status are required
        assert "step_number" in params, f"Missing 'step_number'. Params: {list(params.keys())}"
        assert params["step_number"].default is inspect.Parameter.empty, (
            "step_number should be required (no default)"
        )
        assert "status" in params, f"Missing 'status'. Params: {list(params.keys())}"
        assert params["status"].default is inspect.Parameter.empty, (
            "status should be required (no default)"
        )

        # Then: optional params have defaults
        optional = ["assertion_results", "output_variables", "error_message"]
        for name in optional:
            assert name in params, (
                f"Missing optional param '{name}'. Params: {list(params.keys())}"
            )
            assert params[name].default is not inspect.Parameter.empty, (
                f"'{name}' should be optional (have a default)"
            )

    def test_remaining_tools_have_no_required_params(self) -> None:
        """
        Given the server module
        When inspecting execute_workflow_step, get_workflow_state,
        reset_workflow, and get_workflow_template
        Then they have no required params (or only optional ones)
        """
        # Given: the tools with no required params
        no_required_tools = [
            "execute_workflow_step",
            "get_workflow_state",
            "reset_workflow",
            "get_workflow_template",
        ]

        for tool_name in no_required_tools:
            fn = getattr(server, tool_name, None)
            assert fn is not None, f"server.{tool_name} not found"

            # When: inspecting signature
            sig = inspect.signature(fn)

            # Then: no required params
            required = [
                name
                for name, p in sig.parameters.items()
                if p.default is inspect.Parameter.empty
                and p.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ]
            assert len(required) == 0, (
                f"server.{tool_name} should have no required params, but requires: {required}"
            )


class TestToolExecution:
    """
    REQUIREMENT: Each tool function must accept the documented arguments,
    call the underlying business logic, and return its result as a string.

    WHO: MCP clients sending tools/call requests
    WHAT: Each tool function delegates to the real business logic (parser,
          state manager, etc.) and returns a string — we test our functions
          end-to-end with real inputs
    WHY: If our tool functions don't correctly call the business logic or
         don't return strings, clients get wrong results or type errors

    MOCK BOUNDARY:
        Mock:  Nothing — call our functions with real inputs, get real results
        Real:  Tool functions, business logic, workflow state
        Never: FastMCP dispatch internals
    """

    @pytest.mark.asyncio
    async def test_load_workflow_returns_string_with_step_count(self) -> None:
        """
        Given a valid workflow file
        When calling load_workflow(file_path)
        Then it returns a string containing the step count
        """
        # Given: a valid workflow fixture file
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")

        # When: calling load_workflow
        result = await server.load_workflow(fixture_path)

        # Then: returns a string containing step count info
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "step_count" in result or "step" in result.lower(), (
            f"Result should mention step count. Got: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_execute_workflow_step_returns_enriched_prompt(self) -> None:
        """
        Given a loaded workflow
        When calling execute_workflow_step()
        Then it returns a string containing the enriched prompt
        """
        # Given: a loaded workflow
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")
        await server.load_workflow(fixture_path)

        # When: calling execute_workflow_step
        result = await server.execute_workflow_step()

        # Then: returns a string with prompt content
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "prompt" in result.lower() or "step" in result.lower(), (
            f"Result should contain prompt/step info. Got: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_report_step_result_records_outcome(self) -> None:
        """
        Given a loaded workflow and executed step
        When calling report_step_result(step_number, status)
        Then it records the outcome and returns a string
        """
        # Given: a loaded workflow with step executed
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")
        await server.load_workflow(fixture_path)
        await server.execute_workflow_step()

        # When: reporting the step result
        result = await server.report_step_result(step_number=0, status="passed")

        # Then: returns a string confirming the outcome
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "success" in result.lower() or "complete" in result.lower(), (
            f"Result should confirm success. Got: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_get_workflow_template_includes_description(self) -> None:
        """
        Given a workflow template on disk
        When calling get_workflow_template(task_description="my task")
        Then the template path is resolved internally and the result
        includes the description
        """
        # Given / When: calling with a task description
        result = await server.get_workflow_template(task_description="my task")

        # Then: returns a string including the description
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "my task" in result, f"Result should include task description. Got: {result[:200]}"

    @pytest.mark.asyncio
    async def test_get_workflow_state_returns_string(self) -> None:
        """
        Given a loaded workflow
        When calling get_workflow_state()
        Then it returns a string describing the workflow state
        """
        # Given: a loaded workflow
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")
        await server.load_workflow(fixture_path)

        # When: calling get_workflow_state
        result = await server.get_workflow_state()

        # Then: returns a string with state info
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "step" in result.lower() or "state" in result.lower(), (
            f"Result should describe workflow state. Got: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_reset_workflow_clears_state(self) -> None:
        """
        Given a loaded workflow
        When calling reset_workflow()
        Then it clears state and returns a confirmation string
        """
        # Given: a loaded workflow
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")
        await server.load_workflow(fixture_path)

        # When: calling reset_workflow
        result = await server.reset_workflow()

        # Then: returns a string confirming reset
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "success" in result.lower(), (
            f"Result should confirm reset success. Got: {result[:200]}"
        )


class TestErrorHandling:
    """
    REQUIREMENT: Tool errors must be returned as structured JSON text,
    not raised as exceptions that crash the server.

    WHO: MCP clients that need actionable error information
    WHAT: ActionableError exceptions are caught and returned as ToolResult
          dicts with success=False, a raw error message, an error_type,
          and a separate suggestion field
    WHY: Unhandled exceptions cause the MCP transport to close — clients
         need structured errors to decide whether to retry or report

    MOCK BOUNDARY:
        Mock:  Nothing — use real inputs that trigger real errors
        Real:  Tool functions, error handling wrappers, business logic
        Never: Our own code — don't patch tool functions or wrappers to
               force exceptions; trigger them via real bad inputs
    """

    @pytest.mark.asyncio
    async def test_no_workflow_loaded_returns_structured_error(self) -> None:
        """
        Given no workflow loaded
        When calling execute_workflow_step()
        Then the response dict has success=False, a non-empty error,
        a non-empty error_type, and a non-empty suggestion as separate fields
        """
        # Given: no workflow loaded (reset by conftest)

        # When: calling execute_workflow_step with no workflow
        result = await server.execute_workflow_step()

        # Then: ToolResult-structured error response
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        parsed = ast.literal_eval(result)
        assert parsed["success"] is False, f"Expected success=False. Got: {parsed}"
        assert "error" in parsed and len(parsed["error"]) > 0, (
            f"Expected non-empty 'error' field. Got: {parsed}"
        )
        assert "error_type" in parsed and len(parsed["error_type"]) > 0, (
            f"Expected non-empty 'error_type' field. Got: {parsed}"
        )
        assert "suggestion" in parsed and len(parsed["suggestion"]) > 0, (
            f"Expected non-empty 'suggestion' field. Got: {parsed}"
        )

    @pytest.mark.asyncio
    async def test_get_workflow_state_no_workflow_returns_error(self) -> None:
        """
        Given no workflow loaded
        When calling get_workflow_state()
        Then the response dict has error_type equal to "no_workflow_loaded"
        and contains ToolResult-structured fields
        """
        # Given: no workflow loaded (reset by conftest)

        # When: calling get_workflow_state with no workflow
        result = await server.get_workflow_state()

        # Then: ToolResult-structured error with correct error_type
        parsed = ast.literal_eval(result)
        assert parsed["success"] is False, f"Expected success=False. Got: {parsed}"
        assert parsed["error_type"] == "no_workflow_loaded", (
            f"Expected error_type 'no_workflow_loaded'. Got: {parsed['error_type']}"
        )
        assert "suggestion" in parsed and len(parsed["suggestion"]) > 0, (
            f"Expected non-empty 'suggestion' field. Got: {parsed}"
        )

    @pytest.mark.asyncio
    async def test_reset_workflow_no_workflow_returns_error(self) -> None:
        """
        Given no workflow loaded
        When calling reset_workflow()
        Then the response contains ToolResult-structured fields
        """
        # Given: no workflow loaded (reset by conftest)

        # When: calling reset_workflow with no workflow
        result = await server.reset_workflow()

        # Then: ToolResult-structured error
        parsed = ast.literal_eval(result)
        assert parsed["success"] is False, f"Expected success=False. Got: {parsed}"
        assert parsed["error_type"] == "no_workflow_loaded", (
            f"Expected error_type 'no_workflow_loaded'. Got: {parsed['error_type']}"
        )
        assert "suggestion" in parsed and len(parsed["suggestion"]) > 0, (
            f"Expected non-empty 'suggestion' field. Got: {parsed}"
        )

    @pytest.mark.asyncio
    async def test_report_step_result_no_workflow_returns_error(self) -> None:
        """
        Given no workflow loaded
        When calling report_step_result()
        Then the response contains ToolResult-structured fields
        """
        # Given: no workflow loaded (reset by conftest)

        # When: calling report_step_result with no workflow
        result = await server.report_step_result(step_number=0, status="passed")

        # Then: ToolResult-structured error
        parsed = ast.literal_eval(result)
        assert parsed["success"] is False, f"Expected success=False. Got: {parsed}"
        assert "error_type" in parsed and len(parsed["error_type"]) > 0, (
            f"Expected non-empty 'error_type' field. Got: {parsed}"
        )
        assert "suggestion" in parsed and len(parsed["suggestion"]) > 0, (
            f"Expected non-empty 'suggestion' field. Got: {parsed}"
        )

    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_structured_error(self) -> None:
        """
        Given a non-existent file path
        When calling load_workflow(path)
        Then the response dict has success=False, a non-empty error, a
        non-empty error_type, and a non-empty suggestion as separate fields
        """
        # Given: a path that does not exist
        bad_path = "/nonexistent/path/workflow.md"

        # When: calling load_workflow
        result = await server.load_workflow(bad_path)

        # Then: ToolResult-structured error naming the file
        parsed = ast.literal_eval(result)
        assert parsed["success"] is False, f"Expected success=False. Got: {parsed}"
        assert "error" in parsed and "nonexistent" in parsed["error"].lower(), (
            f"Error should reference the missing file. Got: {parsed}"
        )
        assert "error_type" in parsed and len(parsed["error_type"]) > 0, (
            f"Expected non-empty 'error_type' field. Got: {parsed}"
        )
        assert "suggestion" in parsed and len(parsed["suggestion"]) > 0, (
            f"Expected non-empty 'suggestion' field. Got: {parsed}"
        )

    @pytest.mark.asyncio
    async def test_valid_input_returns_success(self) -> None:
        """
        Given a valid workflow file
        When calling load_workflow(path)
        Then the response is the tool's return value (no error wrapping)
        """
        # Given: a valid workflow fixture
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")

        # When: calling load_workflow
        result = await server.load_workflow(fixture_path)

        # Then: success response
        assert isinstance(result, str), f"Expected str return type, got {type(result).__name__}"
        assert "true" in result.lower() or "success" in result.lower(), (
            f"Success response expected. Got: {result[:200]}"
        )


class TestDocsResource:
    """
    REQUIREMENT: The server must expose a single static MCP resource
    pointing to the GitHub documentation URL.

    WHO: MCP clients that call resources/list and resources/read
    WHAT: One resource function returns the GitHub docs URL; all
          file-reading resource code is removed
    WHY: The file-reading code was dead after pip/uvx install — a static
         link always works and directs users to canonical documentation

    MOCK BOUNDARY:
        Mock:  Nothing — the resource function is pure (returns a string)
        Real:  The get_docs_link() function
        Never: FastMCP resource listing internals
    """

    EXPECTED_URL = "https://github.com/grimlor/workflow-orchestrator-mcp/tree/main/docs"

    def test_get_docs_link_returns_github_url(self) -> None:
        """
        Given the server module
        When calling get_docs_link()
        Then the return value is the GitHub docs URL string
        """
        # Given: the server module
        fn = getattr(server, "get_docs_link", None)
        assert fn is not None, "server module should export 'get_docs_link' function"

        # When: calling get_docs_link
        result = fn()

        # Then: returns the GitHub docs URL
        assert result == self.EXPECTED_URL, (
            f"Expected docs URL '{self.EXPECTED_URL}', got '{result}'"
        )

    def test_no_file_backed_resource_functions_exist(self) -> None:
        """
        Given the server module
        When inspecting for dead resource functions
        Then no file-backed demo resource functions exist
        """
        # Given / When: checking for removed symbols
        dead_symbols = [
            "_read_docs_file",
            "_discover_demo_workflows",
            "list_resources",
            "read_resource",
        ]

        # Then: none of the dead symbols should exist
        for name in dead_symbols:
            assert not hasattr(server, name), (
                f"Dead resource symbol '{name}' should have been removed from server module"
            )


class TestServerEntry:
    """
    REQUIREMENT: The server must start via run() (sync) and main() (async)
    entry points, using stdio transport.

    WHO: Package consumers using uvx or python -m
    WHAT: run() calls mcp.run(transport="stdio"); main() calls
          mcp.run_async(transport="stdio")
    WHY: Entry points are the public contract for starting the server —
         changing them breaks existing MCP client configurations

    MOCK BOUNDARY:
        Mock:  FastMCP.run() / FastMCP.run_async() (3rd-party — we don't
               want to actually start stdio transport in tests)
        Real:  Our run() and main() functions
        Never: Our own wrapper logic around the entry points
    """

    def test_run_invokes_fastmcp_run_with_stdio(self) -> None:
        """
        Given the server module
        When run() is called
        Then FastMCP.run(transport="stdio") is invoked
        """
        # Given: the FastMCP instance
        mcp_instance = getattr(server, "mcp", None)
        assert mcp_instance is not None, "server module should export 'mcp' FastMCP instance"

        # When: calling run() with mocked FastMCP.run
        with patch.object(mcp_instance, "run") as mock_run:
            server.run()

        # Then: FastMCP.run called with stdio transport
        mock_run.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    async def test_main_invokes_fastmcp_run_async_with_stdio(self) -> None:
        """
        Given the server module
        When main() is called
        Then FastMCP.run_async(transport="stdio") is invoked
        """
        # Given: the FastMCP instance
        mcp_instance = getattr(server, "mcp", None)
        assert mcp_instance is not None, "server module should export 'mcp' FastMCP instance"

        # When: calling main() with mocked FastMCP.run_async
        with patch.object(mcp_instance, "run_async", new_callable=AsyncMock) as mock_run_async:
            await server.main()

        # Then: FastMCP.run_async called with stdio transport
        mock_run_async.assert_called_once_with(transport="stdio")
