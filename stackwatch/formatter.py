"""Formatting helpers for stack diffs."""
from __future__ import annotations

from typing import Optional
from stackwatch.differ import FieldDiff, StackDiff, has_changes

_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BOLD = "\033[1m"


def _color(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{code}{text}{_RESET}"


def format_field_diff(name: str, diff: FieldDiff, color: bool = True) -> str:
    parts = [f"  {name}:"]
    if diff.old is None:
        parts.append(_color(f"    + {diff.new}", _GREEN, color))
    elif diff.new is None:
        parts.append(_color(f"    - {diff.old}", _RED, color))
    else:
        parts.append(_color(f"    - {diff.old}", _RED, color))
        parts.append(_color(f"    + {diff.new}", _GREEN, color))
    return "\n".join(parts)


def format_stack_diff(
    diff: StackDiff,
    label_old: str = "old",
    label_new: str = "new",
    color: bool = True,
) -> str:
    header = _color(f"Stack: {diff.stack_name}", _BOLD, color)
    lines = [header, f"  {label_old}  →  {label_new}"]

    if not has_changes(diff):
        lines.append(_color("  No changes detected.", _GREEN, color))
        return "\n".join(lines)

    if diff.status:
        lines.append("  [status]")
        lines.append(format_field_diff("status", diff.status, color=color))

    if diff.parameters:
        lines.append("  [parameters]")
        for key, fd in diff.parameters.items():
            lines.append(format_field_diff(key, fd, color=color))

    if diff.outputs:
        lines.append("  [outputs]")
        for key, fd in diff.outputs.items():
            lines.append(format_field_diff(key, fd, color=color))

    return "\n".join(lines)


def format_no_data(stack_name: str) -> str:
    return f"No data found for stack '{stack_name}' in either environment."
