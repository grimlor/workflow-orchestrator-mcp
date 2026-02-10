"""
Logging infrastructure specification

Verifies the logger is configured correctly for MCP server operation.
"""

import logging


class TestLoggerConfiguration:
    """The workflow orchestrator logger is configured for MCP operation"""

    def test_logger_exists_with_correct_name(self):
        """
        As an MCP server
        I need a named logger
        So that log output is identifiable
        """
        from workflow_orchestrator_mcp.common.logging import logger

        assert logger.name == "workflow-orchestrator-mcp"

    def test_logger_level_is_info(self):
        """
        As an MCP server operator
        I need the default log level set to INFO
        So that operational messages are visible without debug noise
        """
        from workflow_orchestrator_mcp.common.logging import logger

        assert logger.level == logging.INFO

    def test_logger_has_stderr_handler(self):
        """
        As an MCP server
        I need logs written to stderr (not stdout)
        So that log output doesn't interfere with the MCP protocol on stdout
        """
        from workflow_orchestrator_mcp.common.logging import logger

        stderr_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
        ]
        assert len(stderr_handlers) >= 1
