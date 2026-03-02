"""
Workflow template tool & MCP resource specifications

Tests that the server exposes a ``get_workflow_template`` tool the agent can
call autonomously to learn the workflow format, and that MCP resources let
both agent and user browse the format spec, template, and demo workflows.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp.server import (
    call_tool,
    list_resources,
    list_tools,
    read_resource,
)

# ---------------------------------------------------------------------------
# get_workflow_template tool
# ---------------------------------------------------------------------------


class TestGetWorkflowTemplateToolDiscovery:
    """
    REQUIREMENT: Agent discovers the get_workflow_template tool in the tool list.

    WHO: An AI agent connecting to the server for the first time
    WHAT: The tool list includes get_workflow_template with a description that
          explains its purpose and an optional task_description parameter
    WHY: If the agent cannot discover this tool it has no way to learn the
         workflow format after a one-click install
    """

    @pytest.mark.asyncio
    async def test_tool_list_includes_get_workflow_template(self) -> None:
        """
        Given the server is running
        When the agent calls list_tools
        Then get_workflow_template is in the returned tool list
        """
        # Given / When
        tools = await list_tools()

        # Then
        tool_names = [t.name for t in tools]
        assert "get_workflow_template" in tool_names, (
            f"get_workflow_template not found in tool list: {tool_names}"
        )

    @pytest.mark.asyncio
    async def test_tool_count_is_six(self) -> None:
        """
        Given the server is running
        When the agent calls list_tools
        Then there are exactly 6 tools (5 original + get_workflow_template)
        """
        tools = await list_tools()
        assert len(tools) == 6, f"Expected 6 tools, got {len(tools)}"

    @pytest.mark.asyncio
    async def test_tool_has_optional_task_description_param(self) -> None:
        """
        Given the server is running
        When the agent inspects the get_workflow_template schema
        Then task_description is declared but not required
        """
        tools = await list_tools()
        template_tool = next(t for t in tools if t.name == "get_workflow_template")
        schema = template_tool.inputSchema

        assert "task_description" in schema["properties"], (
            "task_description not in input schema properties"
        )
        assert "task_description" not in schema.get("required", []), (
            "task_description should not be required"
        )


class TestGetWorkflowTemplateExecution:
    """
    REQUIREMENT: Calling get_workflow_template returns the format spec,
    skeleton, and example from the resource file on disk.

    WHO: An AI agent that needs to author a new workflow
    WHAT: The tool returns the full template content; when task_description
          is provided it is included in the response; when the template
          file is missing an actionable error is returned
    WHY: This is the primary mechanism for the agent to learn the format
         without the user having to navigate to the repo
    """

    @pytest.mark.asyncio
    async def test_returns_template_content(self) -> None:
        """
        Given the template file exists on disk
        When the agent calls get_workflow_template with no arguments
        Then the response contains the template with format spec and skeleton
        """
        # Given / When
        result = await call_tool("get_workflow_template", {})

        # Then
        text = result[0].text
        assert "WORKFLOW STEP" in text, "Template should contain WORKFLOW STEP marker"
        assert "TOOL" in text, "Template should contain TOOL marker"
        assert "ASSERT" in text, "Template should contain ASSERT marker"
        assert "success" in text.lower(), "Response should indicate success"

    @pytest.mark.asyncio
    async def test_includes_task_description_when_provided(self) -> None:
        """
        Given the template file exists on disk
        When the agent provides a task_description
        Then the response includes the task description and guidance
        """
        # Given / When
        result = await call_tool(
            "get_workflow_template",
            {"task_description": "Audit all open PRs in my org"},
        )

        # Then
        text = result[0].text
        assert "Audit all open PRs" in text, (
            "Response should include the task description"
        )

    @pytest.mark.asyncio
    async def test_works_without_task_description(self) -> None:
        """
        Given the template file exists on disk
        When the agent calls with an empty arguments dict
        Then the template is returned without task-specific guidance
        """
        # Given / When
        result = await call_tool("get_workflow_template", {})

        # Then
        text = result[0].text
        assert "template" in text.lower(), "Response should contain template content"
        assert "WORKFLOW STEP" in text

    @pytest.mark.asyncio
    async def test_returns_error_when_template_missing(self) -> None:
        """
        Given the template file does not exist on disk
        When the agent calls get_workflow_template
        Then an actionable error is returned (not an exception)
        """
        # Given
        with patch(
            "workflow_orchestrator_mcp.server._WORKFLOW_TEMPLATE_PATH",
            Path("/nonexistent/workflow_template.md"),
        ):
            # When
            result = await call_tool("get_workflow_template", {})

        # Then
        text = result[0].text.lower()
        assert "false" in text, "Response should indicate failure"
        assert "not found" in text or "error" in text


class TestGetWorkflowTemplateContent:
    """
    REQUIREMENT: The template file contains all three sections the agent
    needs — format reference, fillable skeleton, and a concrete example.

    WHO: An AI agent reading the template to author a workflow
    WHAT: The template contains section markers for the format quick-reference,
          the skeleton with placeholder steps, and the concrete example
    WHY: Without all three sections the agent would need to make additional
         calls or guess at the format
    """

    @pytest.fixture
    def template_text(self) -> str:
        """Read the actual template file from inside the package."""
        path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "workflow_orchestrator_mcp"
            / "resources"
            / "workflow_template.md"
        )
        return path.read_text(encoding="utf-8")

    def test_contains_format_quick_reference(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it contains the format quick-reference table
        """
        assert "Format Specification" in template_text
        assert "\U0001f527" in template_text  # 🔧
        assert "\U0001f6e0" in template_text  # 🛠

    def test_contains_fillable_skeleton(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it contains a skeleton section with placeholder steps
        """
        assert "Skeleton" in template_text
        assert "<Step 1 name>" in template_text or "<Workflow Title>" in template_text

    def test_contains_concrete_example(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it includes a concrete inline example workflow
        """
        assert "Concrete Example" in template_text
        assert "Simple Repository Lookup" in template_text
        assert "get_file_contents" in template_text

    def test_contains_variable_flow_explanation(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it explains how variables flow between steps
        """
        lower = template_text.lower()
        assert "variable flow" in lower, "Template should explain variable flow"
        assert "report_step_result" in template_text


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------


class TestListResources:
    """
    REQUIREMENT: Server exposes docs and demo workflows as MCP resources.

    WHO: An agent or MCP client browsing available resources
    WHAT: Resources include the format spec and demo workflows when
          present on disk (repo-checkout only); when docs are missing
          the list degrades gracefully
    WHY: Resources let the agent (or user) browse reference material
         without calling a tool
    """

    @pytest.mark.asyncio
    async def test_includes_format_spec_resource(self) -> None:
        """
        Given the docs directory exists
        When the agent lists resources
        Then the workflow format spec is listed
        """
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        assert "workflow://docs/WORKFLOW_FORMAT.md" in uris

    @pytest.mark.asyncio
    async def test_does_not_include_template_resource(self) -> None:
        """
        Given the server is running
        When the agent lists resources
        Then the template is NOT listed (it is served by the tool instead)
        """
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        assert "workflow://docs/workflow_template.md" not in uris

    @pytest.mark.asyncio
    async def test_lists_demo_workflows_when_present(self) -> None:
        """
        Given demo workflow files exist on disk
        When the agent lists resources
        Then at least one demo workflow resource is listed
        """
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        demo_uris = [u for u in uris if u.startswith("workflow://demos/")]
        assert len(demo_uris) >= 1, "Expected at least one demo workflow resource"

    @pytest.mark.asyncio
    async def test_no_demo_resources_when_dir_missing(self) -> None:
        """
        Given the demo workflows directory does not exist
        When the agent lists resources
        Then no demo resources are returned but docs still appear
        """
        with patch(
            "workflow_orchestrator_mcp.server._DEMO_DIR",
            Path("/nonexistent/demo workflows"),
        ):
            resources = await list_resources()

        uris = [str(r.uri) for r in resources]
        demo_uris = [u for u in uris if u.startswith("workflow://demos/")]
        assert len(demo_uris) == 0


class TestReadResource:
    """
    REQUIREMENT: Server returns resource content for valid URIs.

    WHO: An agent reading a specific resource by URI
    WHAT: Format spec and demo workflows are readable;
          unknown URIs produce clear errors
    WHY: Resources are only useful if the agent can actually read them
    """

    @pytest.mark.asyncio
    async def test_read_format_spec(self) -> None:
        """
        Given the format spec exists on disk
        When the agent reads workflow://docs/WORKFLOW_FORMAT.md
        Then the spec content is returned
        """
        content = await read_resource("workflow://docs/WORKFLOW_FORMAT.md")
        assert "WORKFLOW STEP" in content
        assert "TOOL" in content

    @pytest.mark.asyncio
    async def test_read_demo_workflow(self) -> None:
        """
        Given demo workflows exist on disk
        When the agent reads a demo workflow resource
        Then the workflow content is returned
        """
        content = await read_resource("workflow://demos/simple_repo_lookup.md")
        assert "WORKFLOW STEP" in content
        assert "get_file_contents" in content

    @pytest.mark.asyncio
    async def test_read_unknown_demo_raises(self) -> None:
        """
        Given no demo with the requested name exists
        When the agent reads the URI
        Then a ValueError is raised with a clear message
        """
        with pytest.raises(ValueError, match="Demo workflow not found"):
            await read_resource("workflow://demos/does_not_exist.md")

    @pytest.mark.asyncio
    async def test_read_unknown_uri_raises(self) -> None:
        """
        Given a completely unknown URI scheme
        When the agent reads it
        Then a ValueError is raised
        """
        with pytest.raises(ValueError, match="Unknown resource URI"):
            await read_resource("workflow://unknown/path")
