# Simple Repository Lookup Workflow

**Demo**: The simplest possible workflow — one step, one tool, one set of assertions.
Demonstrates basic workflow structure with no variable flow or multi-step dependencies.

*Looks up the `actions/checkout` action repository on GitHub.*

---

## Lookup

### 🔧 WORKFLOW STEP: Look up a GitHub repository
```
Retrieve metadata for the GitHub repository owned by actions named checkout.
Report the repository description, primary language, star count, and license name.
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
