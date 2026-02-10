# Workflow Orchestrator MCP — Architecture

> See the full plan document in `.copilot/Workflow Orchestration MCP Design.md`

## Overview

An MCP server that orchestrates AI workflows defined in markdown. Extends the
demo-assistant-mcp pattern with tool specifications, assertions, variable flow,
and a feedback loop.

## Execution Model

Both this server and demo-assistant-mcp follow the **Copilot-mediated execution
model**: the MCP server crafts prompts, Copilot executes them using available MCP
tools. The orchestrator does **not** invoke tools directly.

The key difference is the **feedback loop**: the orchestrator expects the LLM to
report back after each step via `report_step_result`, enabling step outcome tracking,
variable flow, and assertion evaluation.

## Components

<!-- TODO: Phase 6 — Complete architecture documentation -->
