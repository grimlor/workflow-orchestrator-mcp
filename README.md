# Workflow Orchestrator MCP Server

An MCP server for orchestrating AI workflows defined in markdown with natural language. Evolution from [demo-assistant-mcp](https://github.com/grimlor/demo-assistant-mcp) — adds tool specifications, assertions, variable flow, and a feedback loop.

## Status

🚧 **In Development** — Phase 1: Parser

## Features (Planned)

- **Markdown Workflows**: Define workflows in readable markdown with structured sections
- **Tool Specifications**: Explicit `🛠️ TOOL:` sections tell Copilot which tools to use
- **Assertion Criteria**: `✅ ASSERT:` sections define what "good" looks like
- **Variable Flow**: `📤 OUTPUTS:` and `📥 INPUTS:` pass data between steps
- **Feedback Loop**: LLM reports results back via `report_step_result` callback
- **Step Outcome Tracking**: Passed/failed/skipped per step with per-assertion detail

## Installation

```bash
cd workflow-orchestrator-mcp
uv sync --all-extras
```

## VS Code Configuration

```json
{
  "mcp.servers": {
    "workflow-orchestrator": {
      "command": "uv",
      "args": ["run", "workflow-orchestrator-mcp"],
      "cwd": "/path/to/workflow-orchestrator-mcp",
      "description": "Orchestrate AI workflows defined in markdown"
    }
  }
}
```

## Development

```bash
uv run pytest                    # Run tests
uv run pytest --cov              # Run tests with coverage
uv run ruff check                # Lint
uv run ruff format               # Format
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Workflow Format](docs/WORKFLOW_FORMAT.md)
- [Examples](docs/EXAMPLES.md)

## Related

- [demo-assistant-mcp](https://github.com/grimlor/demo-assistant-mcp) — Parent project for live demo orchestration
