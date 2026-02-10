"""
Enriched prompt builder for workflow steps

Composes enriched prompts from WorkflowStep fields, embedding tool names,
resolved variables, assertion criteria, and callback instructions.
"""

import re
from typing import Any, Dict, List

from .error_handling import ActionableError
from .workflow_state import WorkflowStep


def build_enriched_prompt(
    step: WorkflowStep,
    variables: Dict[str, Any],
) -> str:
    """
    Build an enriched prompt for a workflow step.

    The prompt includes:
    - Step description (with variables resolved)
    - Tool name(s) to invoke
    - Assertion success criteria for the LLM to evaluate
    - Instructions to call report_step_result with outcomes

    Args:
        step: The workflow step to build a prompt for
        variables: Currently available workflow variables

    Returns:
        Enriched prompt text for the LLM

    Raises:
        ActionableError: If a required input variable is missing
    """
    # Validate required inputs are available
    _validate_inputs(step, variables)

    # Resolve variable placeholders in description
    description = _resolve_variables(step.description, variables)

    parts: List[str] = []

    # Step header
    parts.append(f"## Workflow Step {step.step_number + 1}: {step.name}\n")

    # Description
    parts.append(f"{description}\n")

    # Tool instructions
    if len(step.tool_names) == 1:
        parts.append(f"**Use tool:** `{step.tool_names[0]}`\n")
    else:
        parts.append("**Use these tools in order:**")
        for i, tool in enumerate(step.tool_names, 1):
            parts.append(f"  {i}. `{tool}`")
        parts.append("")

    # Input context (resolved values)
    if step.inputs:
        parts.append("**Inputs:**")
        for var_name, description_text in step.inputs.items():
            value = variables.get(var_name, f"[{var_name}]")
            parts.append(f"  - {var_name} = `{value}` ({description_text})")
        parts.append("")

    # Assertion criteria
    if step.assertions:
        parts.append(f"**Success criteria ({len(step.assertions)} assertions to evaluate):**")
        for i, assertion in enumerate(step.assertions, 1):
            parts.append(f"  {i}. {assertion}")
        parts.append("")

    # Output variable instructions
    if step.outputs:
        output_names = list(step.outputs.values())
        parts.append("**Output variables to extract:**")
        for source, target in step.outputs.items():
            parts.append(f"  - Extract `{source}` → report as `{target}`")
        parts.append("")

    # Callback instructions
    parts.append("**After execution**, call `report_step_result` with:")
    parts.append(f"  - step_number: {step.step_number}")
    parts.append('  - status: "passed" or "failed"')

    if step.assertions:
        parts.append(f"  - assertion_results: array of {len(step.assertions)} results, each with:")
        parts.append('    - assertion: the assertion text')
        parts.append('    - passed: true/false')
        parts.append('    - detail: brief explanation of pass/fail')

    if step.outputs:
        output_names = list(step.outputs.values())
        parts.append(f"  - output_variables: object with keys: {', '.join(output_names)}")

    parts.append('  - error_message: "" if passed, or description of failure')

    return "\n".join(parts)


def _validate_inputs(step: WorkflowStep, variables: Dict[str, Any]) -> None:
    """Raise ActionableError if a required input variable is missing."""
    for var_name in step.inputs:
        if var_name not in variables:
            raise ActionableError.variable_missing(var_name, step.name)


def _resolve_variables(text: str, variables: Dict[str, Any]) -> str:
    """Replace [VARIABLE_NAME] placeholders with values from the variable store."""
    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        return match.group(0)  # Leave unresolved if not available

    return re.sub(r"\[([A-Z_]+)\]", replacer, text)
