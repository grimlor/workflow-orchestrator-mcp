"""Shared pytest fixtures for workflow-orchestrator-mcp tests"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator_mcp.common.workflow_state import get_state

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def reset_workflow_state() -> Generator[None]:
    """Reset global workflow state before each test"""
    state = get_state()
    state.file_path = ""
    state.steps = []
    state.current_step = 0
    state.variables.clear()
    state.step_outcomes.clear()
    yield
    # Clean up after test as well
    state = get_state()
    state.file_path = ""
    state.steps = []
    state.current_step = 0
    state.variables.clear()
    state.step_outcomes.clear()


@pytest.fixture
def valid_workflow_markdown() -> str:
    """A well-formed workflow with multiple steps, tools, assertions, and variable flow"""
    return """# Test Workflow

## Discovery Phase

### 🔧 WORKFLOW STEP: Discover repositories
```
Find all repositories in the current project.
```

### 🛠️ TOOL: repository_discovery

### 📤 OUTPUTS:
- result.repositories[0].name → REPO_NAME

### ✅ ASSERT:
- result contains "repositories"
- result.repositories.length > 0

## Setup Phase

### 🔧 WORKFLOW STEP: Set repository context
```
Configure the working context to repository [REPO_NAME]
```

### 🛠️ TOOL: set_repository_context

### 📥 INPUTS:
- REPO_NAME: Repository name from discovery step

### ✅ ASSERT:
- result.success == true

## Action Phase

### 🔧 WORKFLOW STEP: Create pull request
```
Create a PR from feature-branch to main
```

### 🛠️ TOOLS:
- get_current_branch
- create_pull_request

### 📤 OUTPUTS:
- result.pullRequestId → PR_ID

### ✅ ASSERT:
- result.status == "active"
- result.pullRequestId > 0
"""


@pytest.fixture
def simple_workflow_markdown() -> str:
    """A minimal single-step workflow"""
    return """# Simple Workflow

### 🔧 WORKFLOW STEP: Run a single tool
```
Execute the discovery tool and verify results.
```

### 🛠️ TOOL: discovery_tool

### ✅ ASSERT:
- result.success == true
"""


@pytest.fixture
def workflow_without_tools() -> str:
    """A workflow missing tool specifications"""
    return """# Bad Workflow

### 🔧 WORKFLOW STEP: Step with no tool
```
This step has no TOOL section.
```
"""


@pytest.fixture
def empty_workflow_markdown() -> str:
    """A markdown file with no workflow steps"""
    return """# Empty Workflow

This workflow has no executable steps.
"""


@pytest.fixture
def mock_file_system(valid_workflow_markdown: str) -> Generator[tuple[MagicMock, MagicMock]]:
    """Mock file system operations"""
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.read_text") as mock_read:
        mock_exists.return_value = True
        mock_read.return_value = valid_workflow_markdown
        yield mock_exists, mock_read
