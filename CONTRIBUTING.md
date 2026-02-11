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

Tests use pytest with a BDD naming style. Each test file covers a specific concern:

- Place tests in `tests/` with the `test_` prefix
- Use fixtures from `tests/conftest.py` where possible
- Add workflow fixture files to `tests/fixtures/` as needed
- Test both happy paths and error cases

Example:

```python
def test_parser_extracts_step_name_from_heading(sample_workflow):
    """Given a workflow with a named step, the parser extracts the step name."""
    ...
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
