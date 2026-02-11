# Test & Quality Assessment Workflow

**Demo**: Demonstrates multiple tools per step and complex assertions.
Inspects a repository's test infrastructure, CI configuration, and code quality indicators
to produce a comprehensive quality scorecard.

*Runs against `grimlor/workflow-orchestrator-mcp`. Update the owner/repo in Step 1 to target a different repo.*

---

## Phase 1: Discovery

### 🔧 WORKFLOW STEP: Get repository metadata and language
```
Retrieve metadata for the GitHub repository owned by grimlor named workflow-orchestrator-mcp.
Capture the repository name, owner, primary language, and default branch.
```

### 🛠️ TOOL: get_file_contents

### 📤 OUTPUTS:
- result.name → REPO_NAME
- result.owner.login → REPO_OWNER
- result.language → PRIMARY_LANGUAGE
- result.default_branch → DEFAULT_BRANCH

### ✅ ASSERT:
- result contains "name"
- result contains "language"

---

## Phase 2: Test Infrastructure

### 🔧 WORKFLOW STEP: Inspect test directory and configuration
```
Get the file structure of [REPO_OWNER]/[REPO_NAME] and look for:
1. A tests/ or test/ directory — note how many test files exist
2. A test configuration in pyproject.toml, setup.cfg, pytest.ini, or similar
3. Test fixtures or conftest.py files

Report the test framework used, number of test files found, and whether
fixtures/conftest are present.
```

### 🛠️ TOOLS:
- get_repository_tree
- get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.test_file_count → TEST_FILE_COUNT
- result.test_framework → TEST_FRAMEWORK
- result.has_fixtures → HAS_FIXTURES

### ✅ ASSERT:
- a tests/ or test/ directory exists
- at least one test file was found
- a test framework configuration exists (pyproject.toml, pytest.ini, etc.)

---

### 🔧 WORKFLOW STEP: Examine CI/CD pipeline configuration
```
Search the repository [REPO_OWNER]/[REPO_NAME] for CI/CD configuration files:
- .github/workflows/*.yml (GitHub Actions)
- .gitlab-ci.yml (GitLab CI)
- Jenkinsfile (Jenkins)
- azure-pipelines.yml (Azure Pipelines)

For each CI config found, report:
- Which CI system is used
- What triggers the pipeline (push, PR, schedule)
- Whether tests are run in the pipeline
- Whether linting or type checking is included
- Whether coverage is reported
```

### 🛠️ TOOLS:
- get_repository_tree
- get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.ci_system → CI_SYSTEM
- result.runs_tests → CI_RUNS_TESTS
- result.runs_linting → CI_RUNS_LINTING
- result.reports_coverage → CI_REPORTS_COVERAGE

### ✅ ASSERT:
- at least one CI configuration file exists
- the CI pipeline runs tests
- the CI pipeline includes linting or type checking

---

## Phase 3: Code Quality Indicators

### 🔧 WORKFLOW STEP: Check for code quality tooling
```
Examine the configuration files in [REPO_OWNER]/[REPO_NAME] (pyproject.toml, setup.cfg,
.pre-commit-config.yaml, etc.) and determine which code quality tools are configured:

- Linter (ruff, flake8, pylint, eslint, etc.)
- Formatter (black, prettier, ruff format, etc.)
- Type checker (mypy, pyright, typescript strict, etc.)
- Pre-commit hooks

Report which tools are present and their key settings (e.g., strictness level, enabled rules).
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name

### 📤 OUTPUTS:
- result.linter → LINTER_NAME
- result.type_checker → TYPE_CHECKER_NAME
- result.has_precommit → HAS_PRECOMMIT

### ✅ ASSERT:
- at least one linter is configured
- at least one type checker is configured

---

## Phase 4: Quality Scorecard

### 🔧 WORKFLOW STEP: Generate test and quality scorecard
```
Based on all the information gathered, produce a Test & Quality Scorecard for
[REPO_OWNER]/[REPO_NAME] in this format:

## Test & Quality Scorecard: [REPO_OWNER]/[REPO_NAME]

| Category            | Finding                        | Status |
|---------------------|--------------------------------|--------|
| Language            | [PRIMARY_LANGUAGE]             | —      |
| Test Framework      | [TEST_FRAMEWORK]               | ✅/❌  |
| Test Files          | [TEST_FILE_COUNT] files        | ✅/❌  |
| Test Fixtures       | [HAS_FIXTURES]                 | ✅/❌  |
| CI System           | [CI_SYSTEM]                    | ✅/❌  |
| CI Runs Tests       | [CI_RUNS_TESTS]                | ✅/❌  |
| CI Runs Linting     | [CI_RUNS_LINTING]              | ✅/❌  |
| Coverage Reporting  | [CI_REPORTS_COVERAGE]          | ✅/❌  |
| Linter              | [LINTER_NAME]                  | ✅/❌  |
| Type Checker        | [TYPE_CHECKER_NAME]            | ✅/❌  |
| Pre-commit Hooks    | [HAS_PRECOMMIT]                | ✅/❌  |

### Quality Score: X/10

Score rubric:
- Test framework configured: +2
- At least 5 test files: +1
- Fixtures/conftest present: +1
- CI pipeline exists: +1
- CI runs tests: +1
- CI includes linting: +1
- Coverage reporting: +1
- Type checker: +1
- Pre-commit hooks: +1

### Recommendations
- List any gaps or improvements based on missing items
```

### 🛠️ TOOL: get_file_contents

### 📥 INPUTS:
- REPO_OWNER: Repository owner
- REPO_NAME: Repository name
- PRIMARY_LANGUAGE: Primary language
- TEST_FRAMEWORK: Test framework name
- TEST_FILE_COUNT: Number of test files
- HAS_FIXTURES: Whether fixtures exist
- CI_SYSTEM: CI system name
- CI_RUNS_TESTS: Whether CI runs tests
- CI_RUNS_LINTING: Whether CI runs linting
- CI_REPORTS_COVERAGE: Whether CI reports coverage
- LINTER_NAME: Linter name
- TYPE_CHECKER_NAME: Type checker name
- HAS_PRECOMMIT: Whether pre-commit hooks exist

### ✅ ASSERT:
- scorecard includes a table with all quality categories
- scorecard includes a numeric quality score out of 10
- scorecard includes a recommendations section
