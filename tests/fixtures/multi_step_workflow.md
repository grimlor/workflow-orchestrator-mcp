# Multi-Step PR Creation Workflow

## Discovery Phase

### 🔧 WORKFLOW STEP: Discover available repositories
```
Find all repositories in the current project.
Store the first repository name for use in next steps.
```

### 🛠️ TOOL: repository_discovery

### 📤 OUTPUTS:
- result.repositories[0].name → REPO_NAME

### ✅ ASSERT:
- result contains "repositories"
- result.repositories.length > 0

## Context Setup

### 🔧 WORKFLOW STEP: Set repository context
```
Configure the working context to repository [REPO_NAME]
```

### 🛠️ TOOL: set_repository_context

### 📥 INPUTS:
- REPO_NAME: Repository name from discovery step

### ✅ ASSERT:
- result.success == true
- result.repository == "[REPO_NAME]"

## PR Creation

### 🔧 WORKFLOW STEP: Create pull request with validation
```
Create a PR from feature-branch to main with required reviewers
```

### 🛠️ TOOLS:
- get_current_branch
- create_pull_request

### 📤 OUTPUTS:
- result.pullRequestId → PR_ID

### ✅ ASSERT:
- result.status == "active"
- result.pullRequestId > 0
- result.reviewers.length >= 2
