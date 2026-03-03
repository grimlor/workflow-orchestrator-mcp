"""
Workflow template tool specifications

Tests that the server's get_workflow_template function returns the format
spec, skeleton, and example from the resource file on disk, and that the
template file itself contains all required sections.

BDD spec classes:
- TestGetWorkflowTemplateExecution: End-to-end calls to get_workflow_template
- TestGetWorkflowTemplateContent: Template file content verification
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from workflow_orchestrator_mcp import server

# Public API surface (from server.py — post-migration):
#   get_workflow_template(task_description: str | None = None) -> str


class TestGetWorkflowTemplateExecution:
    """
    REQUIREMENT: Calling get_workflow_template returns the format spec,
    skeleton, and example from the resource file on disk.

    WHO: An AI agent that needs to author a new workflow
    WHAT: The function returns the full template content; when
          task_description is provided it is included in the response;
          when the template file is missing an actionable error is returned
    WHY: This is the primary mechanism for the agent to learn the format
         without the user having to navigate to the repo

    MOCK BOUNDARY:
        Mock:  Nothing — call the real function with real inputs
        Real:  get_workflow_template function, template file on disk
        Never: FastMCP dispatch internals
    """

    @pytest.mark.asyncio
    async def test_returns_template_content(self) -> None:
        """
        Given the template file exists on disk
        When calling get_workflow_template() with no arguments
        Then the response contains the template with format spec and skeleton
        """
        # Given / When: calling with no arguments
        result = await server.get_workflow_template()

        # Then: response contains template markers
        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        assert "WORKFLOW STEP" in result, "Template should contain WORKFLOW STEP marker"
        assert "TOOL" in result, "Template should contain TOOL marker"
        assert "ASSERT" in result, "Template should contain ASSERT marker"

    @pytest.mark.asyncio
    async def test_includes_task_description_when_provided(self) -> None:
        """
        Given the template file exists on disk
        When calling get_workflow_template with a task_description
        Then the response includes the task description
        """
        # Given / When: calling with a task description
        result = await server.get_workflow_template(
            task_description="Audit all open PRs in my org"
        )

        # Then: response includes the description
        assert "Audit all open PRs" in result, (
            f"Response should include the task description. Got: {result[:200]}"
        )

    @pytest.mark.asyncio
    async def test_works_without_task_description(self) -> None:
        """
        Given the template file exists on disk
        When calling get_workflow_template with no arguments
        Then the template is returned without task-specific guidance
        """
        # Given / When: calling with no arguments
        result = await server.get_workflow_template()

        # Then: contains template content
        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        assert "WORKFLOW STEP" in result, "Response should contain template content"

    @pytest.mark.asyncio
    async def test_returns_error_when_template_missing(self) -> None:
        """
        Given the template file does not exist on disk
        When calling get_workflow_template
        Then a structured error is returned (not an exception)
        """
        # Given: template path points to nonexistent file
        with patch(
            "workflow_orchestrator_mcp.server._WORKFLOW_TEMPLATE_PATH",
            Path("/nonexistent/workflow_template.md"),
        ):
            # When: calling get_workflow_template
            result = await server.get_workflow_template()

        # Then: structured error response
        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        assert "false" in result.lower() or "error" in result.lower(), (
            f"Should indicate failure. Got: {result[:200]}"
        )


class TestGetWorkflowTemplateContent:
    """
    REQUIREMENT: The template file contains all three sections the agent
    needs — format reference, fillable skeleton, and a concrete example.

    WHO: An AI agent reading the template to author a workflow
    WHAT: The template contains section markers for the format quick-reference,
          the skeleton with placeholder steps, and the concrete example
    WHY: Without all three sections the agent would need to make additional
         calls or guess at the format

    MOCK BOUNDARY:
        Mock:  Nothing — reads the file directly
        Real:  Template file on disk
        Never: Server functions (testing file content, not behavior)
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
        # Given / When: template file content
        # Then: contains format spec markers
        assert "Format Specification" in template_text, (
            "Template should contain Format Specification section"
        )
        assert "\U0001f527" in template_text, (  # 🔧
            "Template should contain 🔧 emoji for workflow steps"
        )
        assert "\U0001f6e0" in template_text, (  # 🛠
            "Template should contain 🛠 emoji for tools"
        )

    def test_contains_fillable_skeleton(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it contains a skeleton section with placeholder steps
        """
        # Given / When: template file content
        # Then: contains skeleton markers
        assert "Skeleton" in template_text, "Template should contain Skeleton section"
        assert "<Step 1 name>" in template_text or "<Workflow Title>" in template_text, (
            "Template should contain placeholder text"
        )

    def test_contains_concrete_example(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it includes a concrete inline example workflow
        """
        # Given / When: template file content
        # Then: contains concrete example
        assert "Concrete Example" in template_text, (
            "Template should contain Concrete Example section"
        )
        assert "Simple Repository Lookup" in template_text, (
            "Template should contain the example workflow title"
        )
        assert "get_file_contents" in template_text, (
            "Template should reference a real tool in the example"
        )

    def test_contains_variable_flow_explanation(self, template_text: str) -> None:
        """
        Given the template file on disk
        When reading its content
        Then it explains how variables flow between steps
        """
        # Given / When: template file content
        # Then: contains variable flow information
        lower = template_text.lower()
        assert "variable flow" in lower, "Template should explain variable flow"
        assert "report_step_result" in template_text, (
            "Template should reference report_step_result for variable passing"
        )
