# Workflow Examples

This document provides an overview of the demo workflows included with the project and guidance for writing your own. All runnable workflow files are in [`docs/demo workflows/`](demo%20workflows/).

---

## Demo Workflows

### 1. Simple Repository Lookup

**File:** [simple_repo_lookup.md](demo%20workflows/simple_repo_lookup.md)

The simplest possible workflow — one step, one tool, basic assertions. Looks up the `actions/checkout` repository on GitHub.

**Features demonstrated:**
- Single step, single tool
- Output variable capture
- Basic assertions

**What happens:**

1. `load_workflow("simple_repo_lookup.md")` parses 1 step
2. `execute_workflow_step()` returns an enriched prompt naming `get_file_contents` with 3 assertions
3. The LLM retrieves the repo metadata, evaluates assertions
4. LLM calls `report_step_result(step_number=0, status="passed", ...)`
5. Workflow completes

---

### 2. PR Review Workflow

**File:** [pr_review_workflow.md](demo%20workflows/pr_review_workflow.md)

A 5-step workflow demonstrating variable flow between steps. Discovers a repository, inspects branches, finds open PRs, reviews recent commits, and produces a PR readiness summary.

**Features demonstrated:**
- Variable flow across 5 steps (`REPO_OWNER`, `REPO_NAME`, `DEFAULT_BRANCH` → downstream steps)
- Multiple tools across different steps
- Summary generation using accumulated variables

---

### 3. Test & Quality Assessment

**File:** [test_quality_assessment.md](demo%20workflows/test_quality_assessment.md)

Inspects a repository's test infrastructure, CI configuration, and code quality indicators to produce a comprehensive quality scorecard with a numeric score.

**Features demonstrated:**
- Multiple tools per step (`get_repository_tree` + `get_file_contents`)
- Complex assertions (checking for CI, linting, type checking)
- Structured scorecard output with scoring rubric

---

### 4. Failure Handling Demo

**File:** [failure_handling_demo.md](demo%20workflows/failure_handling_demo.md)

Intentionally triggers a failure at Step 2 by looking up a nonexistent repository. Demonstrates how the orchestrator halts execution and marks remaining steps as skipped.

**Features demonstrated:**
- Successful step followed by a failing step
- Fail-fast behavior — workflow halts on assertion failure
- Steps 3-4 skipped automatically

**Expected outcome:**

```
Step 0: passed   (actions/checkout lookup succeeds)
Step 1: failed   (nonexistent repo fails assertions)
Step 2: skipped  (depends on failing step's output)
Step 3: skipped  (workflow halted)
```

To retry after failure, call `reset_workflow()` to return to step 0 while keeping the workflow loaded.

---

### 5. GitHub Repository Analysis

**File:** [analyze_github_repo.md](demo%20workflows/analyze_github_repo.md)

A comprehensive 7-step workflow that analyzes `grimlor/workflow-orchestrator-mcp` end-to-end — the orchestrator analyzing itself. Produces a structured assessment of architecture, quality, and health with a score out of 10.

**Features demonstrated:**
- 7-step multi-phase workflow (Discovery → Structure → Quality → Activity → Assessment)
- Rich variable flow throughout
- Natural language assertions
- Self-referential demo (the orchestrator analyzing its own repo)

---

### 6. Azure DevOps MCP Analysis

**File:** [analyze_azure_devops_mcp.md](demo%20workflows/analyze_azure_devops_mcp.md)

The same 7-step analysis workflow targeting `microsoft/azure-devops-mcp`. Compare results with the self-analysis to see how the workflow adapts to a very different project.

**Features demonstrated:**
- Same workflow structure applied to a different repository
- Shows how variable flow and assertions adapt to varying data

---

## Failure Handling Behavior

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

See [WORKFLOW_FORMAT.md](WORKFLOW_FORMAT.md) for the full format specification and test fixtures in [`tests/fixtures/`](../tests/fixtures/) for minimal parsing examples.
