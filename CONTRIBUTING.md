# Contributing to Workflow Orchestrator MCP Server

Thanks for your interest in contributing! This guide covers development setup, code style, and the pull request process.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Getting Started

```bash
# Clone the repository
git clone https://github.com/grimlor/workflow-orchestrator-mcp.git
cd workflow-orchestrator-mcp

# Install all dependencies including dev extras
uv sync --all-extras
```

### Running Quality Checks

```bash
uv run task test                 # Run tests (109 BDD specs)
uv run task cov                  # Run tests with coverage
uv run task lint                 # Lint (with auto-fix)
uv run task format               # Format code
uv run task type                 # Type check
uv run task check                # lint + type + test (all-in-one)
```

> **Note:** `uv run` is optional when the venv is activated via direnv.

All checks must pass before submitting a pull request.

## Code Style

- **Linting**: [Ruff](https://docs.astral.sh/ruff/) with rules E, W, F, I, N, UP, B, SIM, TCH, RUF, PLC0415, PLC2701
- **Line length**: 99 characters max
- **Type hints**: Required on all functions — pyright handles type checking
- **`from __future__ import annotations`**: Required in every Python file
- **Naming**: Follow PEP 8 conventions
- **Assertions**: Every `assert` must include a diagnostic message — bare assertions are prohibited

## Project Structure

```
src/workflow_orchestrator_mcp/
├── server.py                  # MCP server entry point
├── tools/
│   └── workflow_tools.py      # Tool implementations
└── common/
    ├── workflow_parser.py     # Markdown parser
    ├── workflow_state.py      # State management & data structures
    ├── prompt_builder.py      # Enriched prompt composition
    ├── error_handling.py      # ActionableError with suggestions
    └── logging.py             # Logging configuration
```

## Writing Tests

This project follows **Behavior-Driven Development (BDD)** rigorously. Tests are not an afterthought — they are the specification. Understanding this philosophy is essential for getting contributions merged.

### BDD Principles

#### 1. Test Who/What/Why, Not How

Specifications describe **behavioral contracts**, not implementation details.

| Don't | Do |
|-------|-----|
| "When `_plan()` is called internally" | "When planning phase runs, transforms are applied" |
| "Calls `foreachBatch()` with callback" | "Micro-batches are processed through batch phase" |

#### 2. Mock I/O Boundaries Only

**Mock at I/O boundaries:** file system reads, external services, network calls.

**Never mock:** internal helper functions, class methods within the module under test, or pure computation logic.

#### 3. 100% Coverage = Complete Specification

If we don't have 100% test coverage, we have an incomplete specification. Every public method, every code path, every edge case must have a specification describing expected behavior. CI enforces this.

#### 4. Test Public APIs Only

Specifications exercise **only public APIs**. Private/internal functions (`_method`) achieve coverage through public API tests.

| Don't | Do |
|-------|-----|
| `test__parse_internal_state()` | `test_parser_extracts_step_name_from_heading()` |
| `test__build_prompt_fragment()` | `test_enriched_prompt_includes_tool_specification()` |

### Test Organization

Tests are organized by **consumer requirement** — each class covers a specific behavioral concern:

- Place tests in `tests/` with the `test_` prefix
- Group related tests in classes named `Test<RequirementBehavior>`
- Use fixtures from `tests/conftest.py` where possible
- Add workflow fixture files to `tests/fixtures/` as needed
- Test both happy paths and error cases

### Three-Part Contract

Every test requires all three:

1. **Class-level docstring** — REQUIREMENT / WHO / WHAT / WHY / MOCK BOUNDARY
2. **Method-level docstring** — Given / When / Then scenario
3. **Body comments** — `# Given:`, `# When:`, `# Then:` delineating the three phases

### Example

```python
class TestLLMReportsSuccessfulStepOutcome:
    """
    REQUIREMENT: Step outcomes are recorded accurately when the LLM
    reports success.

    WHO: The workflow orchestrator tracking execution progress
    WHAT: When report_step_result is called with status="passed",
          the step is recorded as PASSED with all outputs captured
    WHY: Accurate progress tracking enables variable flow to
         downstream steps and correct workflow completion detection

    MOCK BOUNDARY:
        Mock:  mock_file_system (pathlib.Path — I/O boundary)
        Real:  report_step_result, get_state, workflow state management
        Never: Construct StepOutcome directly — always via report_step_result
    """

    def test_step_recorded_as_passed(self, in_progress_workflow):
        """
        When the LLM reports step 0 as passed with output variables
        Then the step status is PASSED and outputs are captured
        """
        # Given: a workflow in progress (from fixture)
        # When: reporting success for step 0
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[...],
            output_variables={"REPO_NAME": "test-repo"},
        )

        # Then: step is recorded as passed
        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.PASSED, (
            f"Expected PASSED, got {state.step_outcomes[0].status}"
        )
```

## Pull Request Process

1. **Fork** the repository and create a feature branch from `main`
2. **Make your changes** with clear, focused commits
3. **Run all checks** — tests, ruff, pyright must pass
4. **Submit a PR** with a clear description of what and why
5. **Respond to feedback** — maintainers may request changes

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat:` — New features
- `fix:` — Bug fixes
- `docs:` — Documentation changes
- `test:` — Adding or updating tests
- `refactor:` — Code restructuring without behavior change

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include steps to reproduce for bugs
- Include a clear description of expected vs. actual behavior

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
