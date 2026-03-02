# Workflow Template

Use this template to create a new orchestration workflow for the
workflow-orchestrator-mcp server. Replace the placeholder text with
your own steps, tools, variables, and assertions.

---

## Format Specification (Quick Reference)

Each step uses emoji-prefixed markdown headers that the parser recognises:

| Section | Header | Required? |
|---------|--------|-----------|
| Step    | `### 🔧 WORKFLOW STEP: <name>` | yes |
| Description | fenced code block (`` ``` ``) | yes |
| Tool(s) | `### 🛠️ TOOL: <name>` or `### 🛠️ TOOLS:` with a list | yes |
| Inputs  | `### 📥 INPUTS:` with a list | no |
| Outputs | `### 📤 OUTPUTS:` with arrow mappings | no |
| Assertions | `### ✅ ASSERT:` with a list | no |

**Variable placeholders** use `[VARIABLE_NAME]` (uppercase, underscores).
Outputs from one step flow into inputs of later steps via the orchestrator's
variable store.

### Syntax rules

1. Step headers must start with `### 🔧 WORKFLOW STEP:`
2. Descriptions must be in a fenced code block immediately after the header
3. Tool specs use `### 🛠️ TOOL:` (single) or `### 🛠️ TOOLS:` (list)
4. Output arrows: `result.path → VAR_NAME` (both `→` and `->` work)
5. Steps without a tool specification will cause a parse error
6. Use `## Section Title` headings to organise steps into logical phases

### Variable flow

1. Step A declares `📤 OUTPUTS: result.id → ENTITY_ID`
2. The agent calls `report_step_result` with `output_variables: {"ENTITY_ID": "abc123"}`
3. Step B declares `📥 INPUTS: ENTITY_ID` and references `[ENTITY_ID]` in its description
4. When Step B executes, `[ENTITY_ID]` is replaced with `abc123`

---

## Skeleton — replace everything below with your workflow

# <Workflow Title>

<Brief description of what this workflow accomplishes.>

---

## Phase 1

### 🔧 WORKFLOW STEP: <Step 1 name>
```
<Natural language instruction for the agent.
 Reference [VARIABLES] from prior steps if needed.>
```

### 🛠️ TOOL: <tool_name>

### 📥 INPUTS:
- <VARIABLE>: <description of where this comes from>

### 📤 OUTPUTS:
- result.<path> → <VARIABLE_NAME>

### ✅ ASSERT:
- <assertion in natural language or pseudo-code>

---

## Phase 2

### 🔧 WORKFLOW STEP: <Step 2 name>
```
<Instruction referencing [VARIABLE_NAME] captured in Step 1.>
```

### 🛠️ TOOLS:
- <tool_one>
- <tool_two>

### 📥 INPUTS:
- <VARIABLE_NAME>: <description>

### 📤 OUTPUTS:
- result.<path> → <ANOTHER_VARIABLE>

### ✅ ASSERT:
- <assertion>
- <another assertion>

---

## Concrete Example

Below is a minimal, runnable single-step workflow for reference:

# Simple Repository Lookup Workflow

**Demo**: One step, one tool, basic assertions.

---

## Lookup

### 🔧 WORKFLOW STEP: Look up a GitHub repository
```
Retrieve metadata for the GitHub repository owned by actions named checkout.
Report the repository description, primary language, star count, and license.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → REPO_NAME
- result.description → REPO_DESCRIPTION
- result.stargazers_count → STAR_COUNT

### ✅ ASSERT:
- result contains "name"
- result contains "description"
- result.stargazers_count > 0
