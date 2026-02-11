# Contributing to Workflow Orchestrator MCP Server

Thanks for your interest in contributing! This guide covers development setup, code style, and the pull request process.

## Development Setup

### Prerequisites

- Python 3.10+
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
uv run pytest                    # Run tests (77 BDD specs)
uv run pytest --cov              # Run tests with coverage
uv run ruff check src/ tests/    # Lint
uv run mypy src/                 # Type check
```

All checks must pass before submitting a pull request.

## Code Style

- **Linting**: [Ruff](https://docs.astral.sh/ruff/) with rules E, F, I, N, W enabled
- **Line length**: 120 characters max
- **Type hints**: Required on all functions — mypy runs in strict mode
- **Naming**: Follow PEP 8 conventions

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

Specifications describe **behavioral contracts**, not implementation details. Every test uses the format:

```python
def test_<what_happens>_<under_condition>(self):
    """
    As a <who>
    I need <what>
    So that <why>
    """
```

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

Tests are organized by **scenario groups** — each file covers a specific behavioral concern:

- Place tests in `tests/` with the `test_` prefix
- Group related tests in classes named `Test<ScenarioBehavior>`
- Use fixtures from `tests/conftest.py` where possible
- Add workflow fixture files to `tests/fixtures/` as needed
- Test both happy paths and error cases

### Example

```python
"""
Scenario Group 5: Feedback Loop (report_step_result)
"""

class TestLLMReportsSuccessfulStepOutcome:
    """Scenario 5.1: LLM reports successful step outcome"""

    def test_step_recorded_as_passed(self, in_progress_workflow):
        """
        As a workflow orchestrator
        I need the step recorded as passed when the LLM reports success
        So that workflow progress is tracked accurately
        """
        report_step_result(
            step_number=0,
            status="passed",
            assertion_results=[...],
            output_variables={"REPO_NAME": "test-repo"},
        )

        state = get_state()
        assert state.step_outcomes[0].status == StepStatus.PASSED
```

## Pull Request Process

1. **Fork** the repository and create a feature branch from `master`
2. **Make your changes** with clear, focused commits
3. **Run all checks** — tests, ruff, mypy must pass
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
