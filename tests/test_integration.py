"""
FastMCP integration specifications

End-to-end tests that exercise the real FastMCP wiring: decorators,
tool listing, tool dispatch, and resource dispatch. No mocks — these
verify our code wires up correctly with FastMCP.

BDD spec class:
- TestFastMCPIntegration: Real end-to-end through FastMCP test client
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from workflow_orchestrator_mcp.server import mcp

# Public API surface (from server.py — post-migration):
#   mcp: FastMCP("workflow-orchestrator-mcp") instance
#   Tools registered via @mcp.tool() decorators
#   Resources registered via @mcp.resource() decorators

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

EXPECTED_DOCS_URL = "https://github.com/grimlor/workflow-orchestrator-mcp/tree/main/docs"


class TestFastMCPIntegration:
    """
    REQUIREMENT: The full FastMCP wiring — decorators, tool listing,
    tool dispatch, resource listing — must work end-to-end.

    WHO: Developers verifying the migration didn't break the contract
         between our code and FastMCP
    WHAT: A small integration test exercises the real FastMCP instance
          (no mocks) to confirm tools are discoverable, callable, and
          return correct results
    WHY: Unit tests verify our code works — this test verifies it wires
         up correctly with FastMCP, catching decorator misconfiguration,
         schema generation issues, or argument marshalling bugs

    MOCK BOUNDARY:
        Mock:  Nothing — the whole point is real end-to-end
        Real:  FastMCP instance, decorators, tool dispatch, resource dispatch
        Never: Nothing
    """

    @pytest.mark.asyncio
    async def test_list_tools_returns_six_tools(self) -> None:
        """
        Given the real FastMCP server instance
        When listing tools via the test client
        Then six tools are returned with the expected names
        """
        # Given / When: listing tools through FastMCP
        async with Client(mcp) as client:
            tools = await client.list_tools()

        # Then: six tools with expected names
        names = sorted([t.name for t in tools])
        expected = sorted(
            [
                "load_workflow",
                "execute_workflow_step",
                "report_step_result",
                "get_workflow_state",
                "reset_workflow",
                "get_workflow_template",
            ]
        )
        assert names == expected, f"Expected tools {expected}, got {names}"

    @pytest.mark.asyncio
    async def test_call_load_workflow_with_fixture(self) -> None:
        """
        Given the real FastMCP server instance
        When calling load_workflow with a valid fixture file
        Then it returns a result containing the step count
        """
        # Given: a valid fixture file
        fixture_path = str(FIXTURE_DIR / "simple_workflow.md")

        # When: calling load_workflow through FastMCP
        async with Client(mcp) as client:
            result = await client.call_tool("load_workflow", {"file_path": fixture_path})

        # Then: result mentions step count
        result_text = str(result)
        assert "step_count" in result_text or "step" in result_text.lower(), (
            f"Result should contain step info. Got: {result_text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_list_resources_includes_docs(self) -> None:
        """
        Given the real FastMCP server instance
        When listing resources via the test client
        Then a resource with URI workflow://docs is present
        """
        # Given / When: listing resources through FastMCP
        async with Client(mcp) as client:
            resources = await client.list_resources()

        # Then: docs resource is present
        uris = [str(r.uri) for r in resources]
        assert any("workflow://docs" in uri for uri in uris), (
            f"Expected 'workflow://docs' resource. Got URIs: {uris}"
        )

    @pytest.mark.asyncio
    async def test_read_docs_resource_returns_url(self) -> None:
        """
        Given the real FastMCP server instance
        When reading the docs resource
        Then the GitHub docs URL is returned
        """
        # Given / When: reading docs resource through FastMCP
        async with Client(mcp) as client:
            content = await client.read_resource("workflow://docs")

        # Then: returns the GitHub docs URL
        content_text = str(content)
        assert EXPECTED_DOCS_URL in content_text, (
            f"Expected URL '{EXPECTED_DOCS_URL}' in response. Got: {content_text[:200]}"
        )
