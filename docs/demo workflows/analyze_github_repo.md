# GitHub Repository Analysis Workflow

**Demo**: Uses the Workflow Orchestrator MCP to analyze a GitHub repository end-to-end,
producing a structured assessment of architecture, quality, and health.

*This demo runs against `grimlor/workflow-orchestrator-mcp` — the orchestrator analyzing itself.*
*To analyze a different repo, update the owner/repo values in Step 1's description.*

---

## Phase 1: Discovery

### 🔧 WORKFLOW STEP: Get repository metadata
```
Retrieve metadata for the GitHub repository owned by grimlor named workflow-orchestrator-mcp.
Capture the description, primary language, star count, fork count, open issues count,
default branch name, and when the repository was created.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → REPO_NAME
- result.owner.login → REPO_OWNER
- result.description → REPO_DESCRIPTION
- result.language → REPO_LANGUAGE
- result.stargazers_count → REPO_STARS
- result.forks_count → REPO_FORKS
- result.open_issues_count → REPO_OPEN_ISSUES
- result.default_branch → DEFAULT_BRANCH

### ✅ ASSERT:
- result contains "name"
- result contains "description"
- result.description is not null and not empty

---

## Phase 2: Structure Analysis

### 🔧 WORKFLOW STEP: Map the repository file structure
```
Get the complete recursive file tree for the repository [REPO_OWNER]/[REPO_NAME].
Focus on identifying the top-level structure: source directories, test directories,
documentation, configuration files, and CI/CD pipelines.
```

### 🛠️ TOOL: get_repository_tree

### 📥 INPUTS:
- REPO_OWNER: Repository owner from discovery step
- REPO_NAME: Repository name from discovery step

### 📤 OUTPUTS:
- result.tree → FILE_TREE

### ✅ ASSERT:
- result contains "tree"
- result.tree.length > 0

---

### 🔧 WORKFLOW STEP: Read the README
```
Fetch the contents of the README.md file from the default branch of [REPO_OWNER]/[REPO_NAME].
This is the primary documentation entry point.
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.content → README_CONTENT

### ✅ ASSERT:
- result contains "content"
- result.content is not null and not empty
- README contains installation instructions
- README contains usage examples or quick start

---

## Phase 3: Quality Indicators

### 🔧 WORKFLOW STEP: Assess test coverage and CI presence
```
Using the file tree [FILE_TREE], determine:
1. Whether a tests/ or test/ directory exists
2. Whether any CI/CD configuration exists (.github/workflows/, azure-pipelines.yml, etc.)
3. Whether a pyproject.toml, setup.py, package.json, or similar dependency manifest exists
4. Whether documentation beyond README exists (docs/ directory or wiki)
Report each as a boolean finding with supporting evidence from the file tree.
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- FILE_TREE: Full repository file tree from previous step

### 📤 OUTPUTS:
- result.has_tests → HAS_TESTS
- result.has_ci → HAS_CI
- result.has_docs → HAS_DOCS
- result.has_dependency_manifest → HAS_MANIFEST

### ✅ ASSERT:
- result contains "has_tests"
- result contains "has_ci"
- result contains "has_docs"

---

## Phase 4: Activity & Health

### 🔧 WORKFLOW STEP: Check recent commit activity
```
List the 10 most recent commits on the default branch of [REPO_OWNER]/[REPO_NAME].
Identify the date of the most recent commit and the number of unique contributors
in this sample. Note any patterns in commit messages.
```

### 🛠️ TOOL: list_commits

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.commits[0].commit.author.date → LAST_COMMIT_DATE
- result.unique_contributor_count → CONTRIBUTOR_COUNT

### ✅ ASSERT:
- result contains "commits"
- result.commits.length > 0
- most recent commit is within the last 90 days

---

### 🔧 WORKFLOW STEP: Review open issues
```
List up to 10 open issues for [REPO_OWNER]/[REPO_NAME].
Identify recurring themes, any labeled bugs, and whether issues have
been responded to. Note the oldest open issue if any exist.
```

### 🛠️ TOOL: list_issues

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.total_open_issues → OPEN_ISSUE_COUNT
- result.issue_themes → ISSUE_THEMES

### ✅ ASSERT:
- result contains "issues"

---

## Phase 5: Synthesis

### 🔧 WORKFLOW STEP: Generate repository assessment report
```
Using all gathered data, produce a structured assessment report for [REPO_OWNER]/[REPO_NAME].

Repository facts:
- Description: [REPO_DESCRIPTION]
- Language: [REPO_LANGUAGE]
- Stars: [REPO_STARS] | Forks: [REPO_FORKS]
- Open Issues: [REPO_OPEN_ISSUES]
- Last Commit: [LAST_COMMIT_DATE]
- Contributors (recent): [CONTRIBUTOR_COUNT]

Quality indicators:
- Tests present: [HAS_TESTS]
- CI/CD configured: [HAS_CI]
- Docs beyond README: [HAS_DOCS]
- Dependency manifest: [HAS_MANIFEST]

README quality summary: [README_CONTENT]
Issue themes: [ISSUE_THEMES]

Produce a markdown report with the following sections:
1. **Overview** — one paragraph summary of what the project does and its maturity signals
2. **Architecture** — key structural observations from the file tree
3. **Quality Assessment** — test coverage, CI, documentation grade (A/B/C/D/F with rationale)
4. **Health Indicators** — activity recency, contributor breadth, issue responsiveness
5. **Strengths** — 3 concrete positives
6. **Areas for Improvement** — 3 concrete, actionable suggestions
7. **Overall Score** — 1-10 with brief justification

Format the output as clean markdown suitable for a blog post or portfolio page.
```

### 🛠️ TOOLS:
- get_file_contents
- search_code

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name
- REPO_DESCRIPTION: Repository description
- REPO_LANGUAGE: Primary language
- REPO_STARS: Star count
- REPO_FORKS: Fork count
- REPO_OPEN_ISSUES: Open issue count
- LAST_COMMIT_DATE: Date of most recent commit
- CONTRIBUTOR_COUNT: Number of recent unique contributors
- HAS_TESTS: Whether tests directory exists
- HAS_CI: Whether CI/CD configuration exists
- HAS_DOCS: Whether docs directory exists
- HAS_MANIFEST: Whether dependency manifest exists
- README_CONTENT: Full README content
- ISSUE_THEMES: Summary of open issue themes

### 📤 OUTPUTS:
- result.report → ANALYSIS_REPORT

### ✅ ASSERT:
- result contains "report"
- report contains "Overview"
- report contains "Quality Assessment"
- report contains "Overall Score"
- report is at least 500 words
