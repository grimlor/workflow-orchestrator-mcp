# Failure Handling Demo Workflow

**Demo**: Demonstrates what happens when a workflow step fails its assertions.
This workflow intentionally targets a nonexistent repository in Step 2 to trigger
a failure, showing how the orchestrator halts execution and marks remaining steps as skipped.

*Step 1 succeeds. Step 2 is designed to fail. Steps 3-4 should be skipped.*

---

## Phase 1: Successful Step

### 🔧 WORKFLOW STEP: Look up a known repository
```
Retrieve metadata for the GitHub repository owned by actions named checkout.
This is a well-known, public repository that should always exist.
Capture the repository name and description.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → REPO_NAME
- result.description → REPO_DESCRIPTION

### ✅ ASSERT:
- result contains "name"
- result.name == "checkout"

---

## Phase 2: Failing Step

### 🔧 WORKFLOW STEP: Look up a nonexistent repository
```
Retrieve metadata for the GitHub repository owned by grimlor named this-repo-does-not-exist-xyz-12345.
This repository does not exist and should produce an error or empty result.
Capture the repository name if it exists.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → FAKE_REPO_NAME

### ✅ ASSERT:
- result contains "name"
- result.name == "this-repo-does-not-exist-xyz-12345"
- result.stargazers_count > 100

---

## Phase 3: Should Be Skipped

### 🔧 WORKFLOW STEP: Analyze file structure of nonexistent repo
```
Get the file tree for [FAKE_REPO_NAME]. This step depends on the failing step's output
and should never execute — the orchestrator should skip it after Step 2 fails.
```

### 🛠️ TOOL: get_repository_tree

### 📥 INPUTS:
- FAKE_REPO_NAME: Repository name from the failing step

### ✅ ASSERT:
- result contains "tree"

---

## Phase 4: Also Skipped

### 🔧 WORKFLOW STEP: Generate summary report
```
Produce a summary of all findings. This step should also be skipped
because the workflow was halted at Step 2.
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- FAKE_REPO_NAME: Repository name from the failing step
- REPO_NAME: Repository name from Step 1

### ✅ ASSERT:
- summary includes both repository names
- summary is well-formatted markdown
