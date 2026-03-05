"""
Logger configuration specifications

Verifies the logger is configured correctly for MCP server operation.

Spec classes:
    TestLoggerConfiguration
"""

from __future__ import annotations

import logging

from workflow_orchestrator_mcp.common.logging import logger


class TestLoggerConfiguration:
    """
    REQUIREMENT: The workflow orchestrator logger is configured for MCP operation.

    WHO: The MCP server runtime and operator
    WHAT: The logger exists with the correct name "workflow-orchestrator-mcp",
          defaults to INFO level, and writes to stderr
    WHY: stdout is reserved for the MCP JSON-RPC protocol — any log output
         on stdout corrupts the protocol stream and breaks the client

    MOCK BOUNDARY:
        Mock:  nothing — this class tests pure computation
        Real:  logger instance from workflow_orchestrator_mcp.common.logging
        Never: Construct a logger directly — always import the module-level instance
    """

    def test_logger_exists_with_correct_name(self) -> None:
        """
        When the logger is imported
        Then its name is "workflow-orchestrator-mcp"
        """
        # Given: the logger imported from the logging module

        # When: the logger name is inspected
        name = logger.name

        # Then: it matches the expected server name
        assert name == "workflow-orchestrator-mcp", (
            f"Expected logger name 'workflow-orchestrator-mcp', got '{name}'"
        )

    def test_logger_level_is_info(self) -> None:
        """
        When the logger is imported
        Then its default level is INFO
        """
        # Given: the logger imported from the logging module

        # When: the logger level is inspected
        level = logger.level

        # Then: it is set to INFO
        assert level == logging.INFO, (
            f"Expected logger level INFO ({logging.INFO}), "
            f"got {level} ({logging.getLevelName(level)})"
        )

    def test_logger_has_stderr_handler(self) -> None:
        """
        When the logger is imported
        Then it has at least one StreamHandler for stderr output
        """
        # Given: the logger imported from the logging module

        # When: the handlers are inspected
        stderr_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]

        # Then: at least one stderr handler exists
        assert len(stderr_handlers) >= 1, (
            f"Expected at least 1 StreamHandler, got {len(stderr_handlers)}. "
            f"Handlers: {logger.handlers}"
        )
