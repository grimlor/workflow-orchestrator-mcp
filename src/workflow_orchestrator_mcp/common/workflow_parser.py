"""
Markdown parser for workflow scripts

Extracts workflow steps and metadata from markdown files following the format:
    ### 🔧 WORKFLOW STEP: [step name]
    ```
    Step description here
    ```
    ### 🛠️ TOOL: tool_name
    ### 📥 INPUTS: (optional)
    ### 📤 OUTPUTS: (optional)
    ### ✅ ASSERT: (optional)
"""

import re
from pathlib import Path
from typing import Dict, List

from .error_handling import ActionableError
from .workflow_state import WorkflowStep


def parse_workflow_markdown(file_path: str) -> List[WorkflowStep]:
    """
    Parse a workflow markdown file and extract all steps.

    Args:
        file_path: Path to the workflow markdown file

    Returns:
        List of WorkflowStep objects in order

    Raises:
        ActionableError: If file not found, invalid format, or no steps found
    """
    path = Path(file_path)

    if not path.exists():
        raise ActionableError.file_not_found(file_path)

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise ActionableError(
            f"Failed to read workflow file: {e}",
            suggestion="Ensure the file is readable and properly encoded",
        )

    steps = _extract_steps(content, file_path)

    if not steps:
        raise ActionableError.empty_workflow(file_path)

    return steps


def _extract_steps(content: str, file_path: str) -> List[WorkflowStep]:
    """
    Extract all workflow steps from markdown content.

    Each step starts with a WORKFLOW STEP header and includes sections up to
    the next WORKFLOW STEP header (or end of file).
    """
    # Pattern to match step headers: ### 🔧 WORKFLOW STEP: <name>
    step_header_pattern = r"###\s*🔧\s*WORKFLOW STEP:\s*(.+)"
    header_matches = list(re.finditer(step_header_pattern, content))

    if not header_matches:
        return []

    steps: List[WorkflowStep] = []

    for i, match in enumerate(header_matches):
        step_name = match.group(1).strip()

        # Slice content for this step (up to next step header or EOF)
        start = match.end()
        end = header_matches[i + 1].start() if i < len(header_matches) - 1 else len(content)
        section = content[start:end]

        # Extract description from the code block immediately following the header
        description = _extract_description(section, file_path, step_name)

        # Extract tool names
        tool_names = _extract_tools(section, file_path, step_name)

        # Extract optional sections
        inputs = _extract_inputs(section)
        outputs = _extract_outputs(section)
        assertions = _extract_assertions(section)

        # Get the section title (## heading) before this step
        section_title = _get_section_title(content, match.start())

        steps.append(
            WorkflowStep(
                step_number=i,
                name=step_name,
                description=description,
                tool_names=tool_names,
                inputs=inputs,
                outputs=outputs,
                assertions=assertions,
                section_title=section_title,
            )
        )

    return steps


def _extract_description(section: str, file_path: str, step_name: str) -> str:
    """Extract the description from the code block following a step header."""
    code_block = re.search(r"```\s*\n(.*?)```", section, re.DOTALL)
    if not code_block:
        raise ActionableError.invalid_format(
            file_path, f"step '{step_name}' is missing a description code block"
        )
    return code_block.group(1).strip()


def _extract_tools(section: str, file_path: str, step_name: str) -> List[str]:
    """
    Extract tool names from TOOL: or TOOLS: sections.

    Supports:
        ### 🛠️ TOOL: single_tool_name
        ### 🛠️ TOOLS:
        - first_tool
        - second_tool
    """
    # Try multi-tool first (TOOLS: followed by list items)
    multi_match = re.search(r"###\s*🛠️\s*TOOLS:\s*\n((?:\s*-\s*.+\n?)+)", section)
    if multi_match:
        tools_text = multi_match.group(1)
        tools = [line.strip().lstrip("- ").strip() for line in tools_text.strip().splitlines()]
        return [t for t in tools if t]

    # Try single-tool (TOOL: name on same line)
    single_match = re.search(r"###\s*🛠️\s*TOOL:\s*(.+)", section)
    if single_match:
        tool_name = single_match.group(1).strip()
        if tool_name:
            return [tool_name]

    # No tool specification found — this is an error
    raise ActionableError.missing_tool_spec(step_name)


def _extract_inputs(section: str) -> Dict[str, str]:
    """
    Extract input variable specifications from INPUTS: section.

    Format: - VARIABLE_NAME: description text
    """
    inputs: Dict[str, str] = {}
    match = re.search(r"###\s*📥\s*INPUTS:\s*\n((?:\s*-\s*.+\n?)+)", section)
    if match:
        for line in match.group(1).strip().splitlines():
            line = line.strip().lstrip("- ").strip()
            if ":" in line:
                var_name, description = line.split(":", 1)
                inputs[var_name.strip()] = description.strip()
    return inputs


def _extract_outputs(section: str) -> Dict[str, str]:
    """
    Extract output variable mappings from OUTPUTS: section.

    Format: - result.field.path → VARIABLE_NAME
    Returns: {result.field.path: VARIABLE_NAME}
    """
    outputs: Dict[str, str] = {}
    match = re.search(r"###\s*📤\s*OUTPUTS:\s*\n((?:\s*-\s*.+\n?)+)", section)
    if match:
        for line in match.group(1).strip().splitlines():
            line = line.strip().lstrip("- ").strip()
            # Support both → and ->
            if "→" in line:
                source, target = line.split("→", 1)
                outputs[source.strip()] = target.strip()
            elif "->" in line:
                source, target = line.split("->", 1)
                outputs[source.strip()] = target.strip()
    return outputs


def _extract_assertions(section: str) -> List[str]:
    """
    Extract assertion lines from ASSERT: section.

    Format: - assertion text (natural language)
    """
    assertions: List[str] = []
    match = re.search(r"###\s*✅\s*ASSERT:\s*\n((?:\s*-\s*.+\n?)+)", section)
    if match:
        for line in match.group(1).strip().splitlines():
            assertion = line.strip().lstrip("- ").strip()
            if assertion:
                assertions.append(assertion)
    return assertions


def _get_section_title(content: str, position: int) -> str:
    """Extract the most recent ## heading before a given position."""
    before_text = content[:position]
    matches = re.findall(r"^##\s+(.+)$", before_text, re.MULTILINE)
    return matches[-1].strip() if matches else ""
