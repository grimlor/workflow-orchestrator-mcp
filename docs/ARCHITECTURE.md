# Workflow Orchestrator MCP — Architecture

## Overview

An MCP server that orchestrates AI workflows defined in markdown with natural language. Extends the [demo-assistant-mcp](https://github.com/grimlor/demo-assistant-mcp) pattern with tool specifications, assertion-based validation, variable flow between steps, and an LLM feedback loop.

## Execution Model

Both this server and demo-assistant-mcp follow the **Copilot-mediated execution model**: the MCP server crafts prompts, Copilot executes them using available MCP tools. The orchestrator does **not** invoke tools directly.

The key difference is the **feedback loop**. Where demo-assistant delivers prompts as fire-and-forget, the workflow orchestrator expects the LLM to report back after each step via `report_step_result`. This enables:

- **Step outcome tracking** — passed/failed/skipped per step
- **Assertion evaluation** — LLM evaluates success criteria and reports per-assertion results
- **Variable flow** — LLM extracts output values that feed into subsequent steps

```
┌───────────────────┐     enriched prompt      ┌──────────────────┐
│                   │  ──────────────────────► │                  │
│   Orchestrator    │                          │  Copilot / LLM   │
│   (MCP Server)    │  ◄────────────────────── │                  │
│                   │    report_step_result    │  (executes tools │
│  - parse workflow │                          │   evaluates      │
│  - track state    │                          │   assertions)    │
│  - manage vars    │                          │                  │
└───────────────────┘                          └──────────────────┘
```

## Components

### Server (`server.py`)

The MCP server entry point. Registers five tools with the MCP protocol and routes calls to the appropriate tool functions. Handles error responses by catching `ActionableError` exceptions and returning structured error text.

### Tools (`tools/workflow_tools.py`)

The five MCP tools exposed to the LLM:

| Tool | Description |
|------|-------------|
| `load_workflow` | Load and parse a workflow markdown file. Returns step count and first step info. |
| `execute_workflow_step` | Build an enriched prompt for the current step with tool specs, variables, and assertion criteria. |
| `report_step_result` | **Callback tool** — LLM reports step outcomes. Records pass/fail, merges output variables, returns next step or completion. |
| `get_workflow_state` | Return current workflow progress: completed/failed/pending steps, variables, assertion results. |
| `reset_workflow` | Reset to beginning while keeping the workflow loaded. |

### Common Modules

#### `workflow_parser.py`

Parses markdown files with the extended workflow format. Extracts:
- Step headers (`### 🔧 WORKFLOW STEP:`)
- Descriptions (fenced code blocks)
- Tool specifications (`🛠️ TOOL:` / `🛠️ TOOLS:`)
- Input/output declarations (`📥 INPUTS:` / `📤 OUTPUTS:`)
- Assertions (`✅ ASSERT:`)

Raises `ActionableError` for missing files, invalid formats, and missing tool specifications.

#### `workflow_state.py`

Manages execution state with these data structures:

- **`WorkflowStep`** — Parsed step with name, description, tool names, inputs, outputs, assertions
- **`StepOutcome`** — LLM-reported result with status, per-assertion results, output variables
- **`AssertionResult`** — Single assertion's pass/fail with LLM-provided detail
- **`StepStatus`** — Enum: `not_started`, `in_progress`, `passed`, `failed`, `skipped`
- **`WorkflowState`** — Singleton tracking steps, current position, variables, and outcomes

State follows a global singleton pattern — one workflow execution at a time per MCP server instance.

#### `prompt_builder.py`

Composes enriched prompts from `WorkflowStep` fields:

1. Resolves `[VARIABLE]` placeholders with values from prior steps
2. Validates required input variables are available
3. Embeds tool names, assertion criteria, and output extraction instructions
4. Includes `report_step_result` callback instructions with expected schema

#### `error_handling.py`

Extends the demo-assistant-mcp error pattern with workflow-specific error types:

| Error Type | When |
|-----------|------|
| `file_not_found` | Workflow file doesn't exist |
| `invalid_format` | Markdown doesn't follow expected structure |
| `empty_workflow` | No workflow steps found in file |
| `missing_tool_spec` | Step has no `🛠️ TOOL:` section |
| `variable_missing` | Required input variable not set by prior steps |
| `step_out_of_order` | LLM reports results for wrong step number |
| `no_workflow_loaded` | Tool called before `load_workflow` |

Each error includes a `suggestion` field with actionable guidance for the LLM.

#### `logging.py`

Shared logging configuration (reused from demo-assistant-mcp). Logs to stderr at INFO level.

## Execution Flow

1. **Load** — LLM calls `load_workflow("path/to/workflow.md")`. Parser extracts steps.
2. **Execute** — LLM calls `execute_workflow_step()`. Orchestrator returns enriched prompt for step 0.
3. **LLM acts** — LLM reads the prompt, invokes the specified tool(s), evaluates assertion criteria.
4. **Report** — LLM calls `report_step_result(step_number=0, status="passed", ...)`.
5. **Next step** — Orchestrator records outcome, merges output variables, returns next step's prompt.
6. **Repeat** — Steps 3–5 repeat until all steps complete or a step fails.
7. **On failure** — Remaining steps are marked as skipped. LLM can call `get_workflow_state()` for the full report.

## Architectural Tradeoffs

### LLM-Evaluated Assertions

Assertions are evaluated by the LLM, not a programmatic engine. This means they are human-readable intent (like Gherkin), not deterministic predicates. Two runs could theoretically produce different pass/fail decisions. This is an acceptable tradeoff — it keeps the system language-agnostic and avoids building an expression evaluator.

### Singleton State

One workflow at a time per server instance. State is in-memory only — restarting the server loses state. Cross-session resume and concurrent execution are deferred to post-MVP.

### Fail-Fast

On step failure, remaining steps are marked as skipped. No retry logic in MVP. The LLM can call `reset_workflow()` and re-run within the same session.

## Comparison with demo-assistant-mcp

| Aspect | demo-assistant-mcp | workflow-orchestrator-mcp |
|--------|-------------------|--------------------------|
| **Purpose** | Live presentation orchestration | Automated workflow execution |
| **Execution** | Human confirms each step | Auto-execute entire workflow |
| **Tool Invocation** | Returns prompt to Copilot | Returns enriched prompt with tool specs and criteria |
| **Validation** | None (human observes) | LLM evaluates assertions, reports back via callback |
| **Data Flow** | `[VARIABLE]` substitution | Structured `INPUTS`/`OUTPUTS` with LLM-managed variable flow |
| **Error Handling** | Human decides next action | Step outcome tracking, fail-fast |
| **Feedback Loop** | None (one-way prompt delivery) | LLM reports results back via `report_step_result` |
