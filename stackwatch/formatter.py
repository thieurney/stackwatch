"""Formatting utilities for rendering stack diffs to the terminal."""

from typing import Optional
from stackwatch.differ import StackDiff, FieldDiff, has_changes

TRESET = "\033[0m"
TRED = "\033[31m"
TGREEN = "\033[32m"
TYELLOW = "\033[33m"
TBOLD = "\033[1m"


def _color(text: str, color: str, use_color: bool = True) -> str:
    if not use_color:
        return text
    return f"{color}{text}{TRESET}"


def format_field_diff(field: str, diff: FieldDiff, use_color: bool = True) -> str:
    old = repr(diff.old_value) if diff.old_value is not None else "<missing>"
    new = repr(diff.new_value) if diff.new_value is not None else "<missing>"
    label = f"  {field}:"
    old_str = _color(f"- {old}", TRED, use_color)
    new_str = _color(f"+ {new}", TGREEN, use_color)
    return f"{label}\n    {old_str}\n    {new_str}"


def format_stack_diff(
    diff: StackDiff,
    stack_name: str,
    env_a: str = "env-a",
    env_b: str = "env-b",
    use_color: bool = True,
) -> str:
    lines = []
    header = _color(f"Stack: {stack_name}  ({env_a} → {env_b})", TBOLD, use_color)
    lines.append(header)

    if not has_changes(diff):
        lines.append(_color("  No differences found.", TGREEN, use_color))
        return "\n".join(lines)

    if diff.status:
        lines.append(_color("  [status]", TYELLOW, use_color))
        lines.append(format_field_diff("status", diff.status, use_color))

    if diff.parameters:
        lines.append(_color("  [parameters]", TYELLOW, use_color))
        for key, fd in sorted(diff.parameters.items()):
            lines.append(format_field_diff(key, fd, use_color))

    if diff.outputs:
        lines.append(_color("  [outputs]", TYELLOW, use_color))
        for key, fd in sorted(diff.outputs.items()):
            lines.append(format_field_diff(key, fd, use_color))

    return "\n".join(lines)


def format_no_data(stack_name: str, env: str, use_color: bool = True) -> str:
    msg = f"Stack '{stack_name}' not found in {env}."
    return _color(msg, TRED, use_color)
