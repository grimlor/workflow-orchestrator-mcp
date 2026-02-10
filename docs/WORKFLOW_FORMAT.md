# Workflow Format Specification

Workflows are defined in standard markdown files with special tagged sections that the orchestrator parses into executable steps.

## Step Structure

Each workflow step follows this structure:

```markdown
### 🔧 WORKFLOW STEP: [descriptive name]
` ` `
Natural language description of what this step does.
Can reference [VARIABLES] from prior steps.
` ` `

### 🛠️ TOOL: tool_name

### 📥 INPUTS: (optional)
- variable_name: description of expected input

### 📤 OUTPUTS: (optional)
- result.field.path → VARIABLE_NAME

### ✅ ASSERT: (optional)
- result contains "expected_field"
- result.status == "success"
- PR has at least 2 reviewers
```

## Section Reference

### Step Header (required)

```markdown
### 🔧 WORKFLOW STEP: Discover available repositories
```

Every step must start with this header. The text after the colon becomes the step name.

### Description (required)

````markdown
```
Natural language description of what this step does.
Can reference [REPO_NAME] variables set by prior steps.
```
````

A fenced code block immediately following the step header. This is the core instruction the LLM will act on. Variable placeholders like `[REPO_NAME]` are resolved at runtime.

### Tool Specification (required)

**Single tool:**
```markdown
### 🛠️ TOOL: repository_discovery
```

**Multiple tools:**
```markdown
### 🛠️ TOOLS:
- get_current_branch
- create_pull_request
```

Every step must specify at least one tool. Multiple tools are invoked sequentially in the order listed. Tool names should match MCP tools available to Copilot.

### Inputs (optional)

```markdown
### 📥 INPUTS:
- REPO_NAME: Repository name from discovery step
- BRANCH: Target branch for the pull request
```

Declares variables this step requires from prior steps. The orchestrator validates these are available before building the prompt. If a required variable hasn't been set, an `ActionableError` is raised.

### Outputs (optional)

```markdown
### 📤 OUTPUTS:
- result.repositories[0].name → REPO_NAME
- result.pullRequestId → PR_ID
```

Instructs the LLM to extract values from the tool's results and report them back via `report_step_result`. The left side is guidance for the LLM on where to find the value; the right side is the variable name stored in workflow state. Both `→` and `->` arrows are supported.

### Assertions (optional)

```markdown
### ✅ ASSERT:
- result.success == true
- result.repositories.length > 0
- PR has at least 2 reviewers
```

Natural language success criteria. Each line becomes a separate assertion the LLM evaluates after executing the step. Assertions can be:

- **Pseudo-code expressions**: `result.count > 0`, `result.status == "active"`
- **Natural language criteria**: `PR has at least 2 reviewers`, `Report URL is a valid HTTPS link`

The LLM reports each assertion as passed/failed with a brief explanation.

## Workflow Organization

### Sections

Use level-2 headings (`##`) to organize steps into logical phases:

```markdown
# My Workflow

## Discovery Phase

### 🔧 WORKFLOW STEP: Find repositories
...

## Setup Phase

### 🔧 WORKFLOW STEP: Configure context
...
```

Section titles are extracted and stored with each step for reporting purposes.

### Step Numbering

Steps are numbered automatically (0-based) in the order they appear in the file. The step number is used when calling `report_step_result`.

## Syntax Rules

1. **Step headers** must start with `### 🔧 WORKFLOW STEP:`
2. **Descriptions** must be in a fenced code block (triple backticks) immediately after the header
3. **Tool specs** must use either `### 🛠️ TOOL:` (single) or `### 🛠️ TOOLS:` (multiple with dash-prefixed list)
4. **Inputs/Outputs** are optional — use when steps need data from or provide data to other steps
5. **Assertions** are optional — use to define what "success" looks like for a step
6. **Variable placeholders** use the format `[VARIABLE_NAME]` (uppercase with underscores)
7. Steps without tool specifications will cause a parse error

## Variable Flow

Variables flow between steps through the OUTPUTS → INPUTS mechanism:

1. Step A declares `📤 OUTPUTS: result.id → ENTITY_ID`
2. The enriched prompt instructs the LLM to extract this value
3. The LLM calls `report_step_result` with `output_variables: {"ENTITY_ID": "abc123"}`
4. The orchestrator stores `ENTITY_ID = "abc123"` in workflow state
5. Step B declares `📥 INPUTS: ENTITY_ID: ...` and references `[ENTITY_ID]` in its description
6. When Step B runs, `[ENTITY_ID]` is replaced with `abc123`
