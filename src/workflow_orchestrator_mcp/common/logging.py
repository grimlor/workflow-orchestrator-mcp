"""
Logging configuration for workflow-orchestrator-mcp

Sets up standard logging to stderr for MCP server operation.
"""

import logging
import sys

# Create logger
logger = logging.getLogger("workflow-orchestrator-mcp")
logger.setLevel(logging.INFO)

# Create handler to stderr (MCP servers use stderr for logs, stdout for protocol)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

# Export logger
__all__ = ["logger"]
