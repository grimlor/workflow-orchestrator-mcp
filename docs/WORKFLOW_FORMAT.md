# Workflow Format Specification

> See the full specification in `.copilot/Workflow Orchestration MCP Design.md`

## Quick Reference

```markdown
### 🔧 WORKFLOW STEP: [descriptive name]
\```
Natural language description of what this step does.
Can reference [VARIABLES] from prior steps.
\```

### 🛠️ TOOL: tool_name
*or*
### 🛠️ TOOLS:
- first_tool_name
- second_tool_name

### 📥 INPUTS: (optional)
- variable_name: description of expected input

### 📤 OUTPUTS: (optional)
- result.field.path → VARIABLE_NAME

### ✅ ASSERT: (optional)
- result contains "expected_field"
- result.status == "success"
- PR has at least 2 reviewers
```

<!-- TODO: Phase 6 — Complete format documentation with examples -->
