# Multi-Step PR Review Workflow

**Demo**: Demonstrates variable flow between steps — each step builds on data from prior steps.
Discovers a repository, inspects its branches, finds open pull requests, and reviews the most
recent PR with a summary of changes.

*Runs against `grimlor/workflow-orchestrator-mcp`. Update the owner/repo in Step 1 to target a different repo.*

---

## Phase 1: Discovery

### 🔧 WORKFLOW STEP: Get repository metadata
```
Retrieve metadata for the GitHub repository owned by grimlor named workflow-orchestrator-mcp.
Capture the repository name, owner, default branch, and description.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → REPO_NAME
- result.owner.login → REPO_OWNER
- result.default_branch → DEFAULT_BRANCH

### ✅ ASSERT:
- result contains "name"
- result contains "default_branch"

---

## Phase 2: Branch Exploration

### 🔧 WORKFLOW STEP: List repository branches
```
List all branches for the repository [REPO_OWNER]/[REPO_NAME].
Identify how many branches exist and note each branch name.
```

### 🛠️ TOOL: list_branches

### 📥 INPUTS:
- REPO_OWNER: Repository owner from discovery step
- REPO_NAME: Repository name from discovery step

### 📤 OUTPUTS:
- result.total_count → BRANCH_COUNT

### ✅ ASSERT:
- result contains at least one branch
- a branch named the same as DEFAULT_BRANCH exists

---

## Phase 3: Pull Request Discovery

### 🔧 WORKFLOW STEP: Find open pull requests
```
Search for all open pull requests in [REPO_OWNER]/[REPO_NAME].
Report the total count and capture the most recent PR number if any exist.
If no open PRs exist, report that the repository has no open pull requests.
```

### 🛠️ TOOL: search_pull_requests

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.total_count → OPEN_PR_COUNT

### ✅ ASSERT:
- result contains "total_count"
- result.total_count >= 0

---

## Phase 4: Recent Commit Activity

### 🔧 WORKFLOW STEP: Review recent commits on default branch
```
List the 5 most recent commits on the [DEFAULT_BRANCH] branch of [REPO_OWNER]/[REPO_NAME].
For each commit, note the author, date, and commit message.
Summarize the recent development activity: how many unique authors contributed,
what kinds of changes were made (features, fixes, docs, etc.), and overall velocity.
```

### 🛠️ TOOL: list_commits

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name
- DEFAULT_BRANCH: Default branch name

### 📤 OUTPUTS:
- result.total_count → RECENT_COMMIT_COUNT

### ✅ ASSERT:
- result contains at least one commit
- each commit has an author and message

---

## Phase 5: Summary

### 🔧 WORKFLOW STEP: Generate PR readiness summary
```
Based on all the information gathered, produce a concise PR Readiness Summary for
[REPO_OWNER]/[REPO_NAME] in this format:

## PR Readiness Summary: [REPO_OWNER]/[REPO_NAME]

| Metric              | Value                |
|---------------------|----------------------|
| Default Branch      | [DEFAULT_BRANCH]     |
| Branch Count        | [BRANCH_COUNT]       |
| Open PRs            | [OPEN_PR_COUNT]      |
| Recent Commits (5)  | [RECENT_COMMIT_COUNT]|

### Observations
- Comment on branching strategy (single branch vs. feature branches)
- Note PR activity level
- Note commit velocity and contributor diversity
- Recommend any improvements to the development workflow
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name
- DEFAULT_BRANCH: Default branch name
- BRANCH_COUNT: Number of branches
- OPEN_PR_COUNT: Number of open PRs
- RECENT_COMMIT_COUNT: Recent commit count

### ✅ ASSERT:
- summary includes a table with all metrics
- summary includes observations section with recommendations
