# Workflow Examples

This document walks through example workflows to demonstrate key features. Working fixture files are also available in `tests/fixtures/`.

---

## 1. Simple Single-Tool Workflow

The simplest possible workflow — one step, one tool, one assertion.

```markdown
# Simple Workflow

### 🔧 WORKFLOW STEP: Run discovery tool
` ` `
Execute the discovery tool and verify it returns results.
` ` `

### 🛠️ TOOL: discovery_tool

### ✅ ASSERT:
- result.success == true
```

**What happens:**

1. `load_workflow("simple_workflow.md")` parses 1 step
2. `execute_workflow_step()` returns an enriched prompt naming `discovery_tool` with one assertion
3. The LLM invokes `discovery_tool`, checks if `result.success == true`
4. LLM calls `report_step_result(step_number=0, status="passed", assertion_results=[...])`
5. Workflow completes

See: [tests/fixtures/simple_workflow.md](../tests/fixtures/simple_workflow.md)

---

## 2. Multi-Step PR Creation with Variable Flow

Demonstrates the core workflow orchestrator value: steps that build on each other through variable flow.

```markdown
# Multi-Step PR Creation Workflow

## Discovery Phase

### 🔧 WORKFLOW STEP: Discover available repositories
` ` `
Find all repositories in the current project.
Store the first repository name for use in next steps.
` ` `

### 🛠️ TOOL: repository_discovery

### 📤 OUTPUTS:
- result.repositories[0].name → REPO_NAME

### ✅ ASSERT:
- result contains "repositories"
- result.repositories.length > 0

## Context Setup

### 🔧 WORKFLOW STEP: Set repository context
` ` `
Configure the working context to repository [REPO_NAME]
` ` `

### 🛠️ TOOL: set_repository_context

### 📥 INPUTS:
- REPO_NAME: Repository name from discovery step

### ✅ ASSERT:
- result.success == true
- result.repository == "[REPO_NAME]"

## PR Creation

### 🔧 WORKFLOW STEP: Create pull request with validation
` ` `
Create a PR from feature-branch to main with required reviewers
` ` `

### 🛠️ TOOLS:
- get_current_branch
- create_pull_request

### 📤 OUTPUTS:
- result.pullRequestId → PR_ID

### ✅ ASSERT:
- result.status == "active"
- result.pullRequestId > 0
- result.reviewers.length >= 2
```

**What happens:**

1. **Step 0** — LLM calls `repository_discovery`, extracts `REPO_NAME` from results, reports back
2. **Step 1** — Orchestrator substitutes `[REPO_NAME]` in the description. LLM calls `set_repository_context` with the discovered repo name
3. **Step 2** — LLM calls `get_current_branch` then `create_pull_request`, extracts `PR_ID`, evaluates 3 assertions

**Variable flow:** `REPO_NAME` flows from Step 0 → Step 1. `PR_ID` is captured in Step 2 for potential downstream use.

See: [tests/fixtures/multi_step_workflow.md](../tests/fixtures/multi_step_workflow.md)

---

## 3. Data Quality Validation with Complex Assertions

Demonstrates multiple assertions and cross-step data dependencies.

```markdown
# Data Quality Workflow

## Validation Phase

### 🔧 WORKFLOW STEP: Validate data quality
` ` `
Run data quality checks on the target dataset.
Verify row count, null percentage, and schema compliance.
` ` `

### 🛠️ TOOL: data_quality_check

### ✅ ASSERT:
- result.row_count > 1000
- result.null_percentage < 5
- result.schema_valid == true
- result contains "quality_score"

## Report Phase

### 🔧 WORKFLOW STEP: Generate quality report
` ` `
Generate a summary report of data quality results.
` ` `

### 🛠️ TOOLS:
- generate_report
- send_notification

### 📥 INPUTS:
- QUALITY_SCORE: Overall quality score from validation

### 📤 OUTPUTS:
- result.report_url → REPORT_URL

### ✅ ASSERT:
- result.report_url starts with "https://"
- result.notification_sent == true
```

**Key features demonstrated:**
- **4 assertions on a single step** — the LLM evaluates each independently
- **Multi-tool step** — `generate_report` and `send_notification` called in order
- **Natural language assertions** — `result.report_url starts with "https://"` is not code, it's human-readable intent that the LLM interprets

See: [tests/fixtures/workflow_with_assertions.md](../tests/fixtures/workflow_with_assertions.md)

---

## 4. Failure Handling

When a step fails its assertions, the orchestrator halts execution and marks remaining steps as skipped.

**Example interaction with a 4-step workflow where step 2 fails:**

```
LLM → load_workflow("my_workflow.md")
       ← 4 steps loaded, first step prompt returned

LLM → execute_workflow_step()
       ← Enriched prompt for step 0

LLM → report_step_result(step_number=0, status="passed", ...)
       ← Next prompt for step 1

LLM → report_step_result(step_number=1, status="failed",
         assertion_results=[
           {"assertion": "result.count > 0", "passed": false,
            "detail": "result.count was 0, no records returned"}
         ],
         error_message="Data quality check returned empty results")
       ← Failure summary, workflow halted

LLM → get_workflow_state()
       ← Step 0: passed, Step 1: failed, Steps 2-3: skipped
```

The execution report from `get_workflow_state()` shows:
- Which step failed and why
- Per-assertion detail explaining the failure
- Remaining steps marked as skipped

To retry, call `reset_workflow()` to return to step 0 while keeping the workflow loaded.

---

## Writing Your Own Workflows

1. **Start with the goal** — What should happen end-to-end?
2. **Identify the tools** — Which MCP tools will the LLM invoke at each stage?
3. **Define data flow** — What values need to pass between steps?
4. **Write assertions** — What does "success" look like for each step?
5. **Test incrementally** — Load the workflow and step through it to verify parsing

### Tips

- Keep step descriptions clear and concise — the LLM reads them as instructions
- Use natural language for assertions — `result has at least 3 items` works as well as `result.length >= 3`
- Name variables descriptively — `REPO_NAME` is better than `VAR1`
- Organize related steps under `##` section headings for readability
- One tool per step is simplest; use multi-tool steps when operations are tightly coupled
