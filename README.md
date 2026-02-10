# Workflow Orchestrator MCP Server

An MCP server for orchestrating AI workflows defined in markdown with natural language. Evolution from [demo-assistant-mcp](https://github.com/grimlor/demo-assistant-mcp) — adds tool specifications, assertion-based validation, variable flow between steps, and an LLM feedback loop.

## How It Works

Define workflows in readable markdown. The orchestrator parses them into steps and feeds enriched prompts to Copilot, which executes the specified tools. After each step, the LLM reports results back, and the orchestrator tracks outcomes and flows data to the next step.

```
  Workflow.md          Orchestrator             Copilot / LLM
  ┌──────────┐    ┌──────────────────┐    ┌──────────────────────┐
  │ Step 1   │──► │ Parse & build    │──► │ Execute tools        │
  │ Step 2   │    │ enriched prompt  │◄── │ Evaluate assertions  │
  │ Step 3   │    │ Track outcomes   │    │ Report via callback  │
  └──────────┘    └──────────────────┘    └──────────────────────┘
```

### Key Concepts

- **Enriched prompts** — Each step becomes a prompt with tool names, resolved variables, assertion criteria, and callback instructions
- **Feedback loop** — The LLM calls `report_step_result` after each step, reporting pass/fail and extracted output variables
- **Variable flow** — Output values from one step (`📤 OUTPUTS:`) become input values for the next (`📥 INPUTS:`)
- **Assertion evaluation** — Natural language success criteria evaluated by the LLM, not a programmatic engine

## Quick Example

```markdown
### 🔧 WORKFLOW STEP: Discover repositories
` ` `
Find all repositories in the current project.
` ` `

### 🛠️ TOOL: repository_discovery

### 📤 OUTPUTS:
- result.repositories[0].name → REPO_NAME

### ✅ ASSERT:
- result contains "repositories"
- result.repositories.length > 0
```

See [Workflow Format](docs/WORKFLOW_FORMAT.md) for the full specification and [Examples](docs/EXAMPLES.md) for walkthroughs.

## MCP Tools

| Tool | Description |
|------|-------------|
| `load_workflow` | Load and parse a workflow markdown file |
| `execute_workflow_step` | Get the enriched prompt for the current step |
| `report_step_result` | LLM reports step outcomes back to the orchestrator |
| `get_workflow_state` | View workflow progress, variables, and assertion results |
| `reset_workflow` | Reset to the beginning (workflow stays loaded) |

## Installation

```bash
cd workflow-orchestrator-mcp
uv sync --all-extras
```

## VS Code / Copilot Configuration

Add to your VS Code settings or `.vscode/mcp.json`:

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
uv run pytest                    # Run tests (77 BDD specs)
uv run pytest --cov              # Run tests with coverage
uv run ruff check src/ tests/    # Lint
uv run mypy src/                 # Type check
```

### Project Structure

```
src/workflow_orchestrator_mcp/
├── server.py                  # MCP server entry point
├── tools/
│   └── workflow_tools.py      # Tool implementations
└── common/
    ├── workflow_parser.py     # Markdown parser
    ├── workflow_state.py      # State management & data structures
    ├── prompt_builder.py      # Enriched prompt composition
    ├── error_handling.py      # ActionableError with suggestions
    └── logging.py             # Logging configuration
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — Execution model, components, and design decisions
- [Workflow Format](docs/WORKFLOW_FORMAT.md) — Complete markdown format specification
- [Examples](docs/EXAMPLES.md) — Walkthrough examples with explanations

## Comparison with demo-assistant-mcp

| Aspect | demo-assistant-mcp | workflow-orchestrator-mcp |
|--------|-------------------|--------------------------|
| **Purpose** | Live presentation orchestration | Automated workflow execution |
| **Execution** | Human confirms each step | Auto-execute entire workflow |
| **Validation** | None (human observes) | LLM evaluates assertions, reports back |
| **Data Flow** | `[VARIABLE]` substitution | Structured INPUTS/OUTPUTS with LLM-managed variable flow |
| **Feedback Loop** | None (one-way) | LLM reports results via `report_step_result` |

Both projects follow the **Copilot-mediated execution model** — the MCP server crafts prompts, Copilot executes them. Neither server invokes tools directly.

## Related

- [demo-assistant-mcp](https://github.com/grimlor/demo-assistant-mcp) — Parent project for live demo orchestration
