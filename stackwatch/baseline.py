"""Baseline comparison: compare current stack state against a saved baseline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState
from stackwatch.differ import StackDiff, diff_stacks, has_changes


@dataclass
class BaselineReport:
    stack_name: str
    baseline_label: str
    diff: Optional[StackDiff]
    baseline_missing: bool = False
    current_missing: bool = False
    issues: List[str] = field(default_factory=list)


def drifted_from_baseline(report: BaselineReport) -> bool:
    """Return True when the current state differs from the baseline."""
    if report.baseline_missing or report.current_missing:
        return True
    return report.diff is not None and has_changes(report.diff)


def build_baseline_report(
    stack_name: str,
    baseline_label: str,
    baseline: Optional[StackState],
    current: Optional[StackState],
) -> BaselineReport:
    """Compare *current* against *baseline* and return a structured report."""
    issues: List[str] = []

    if baseline is None:
        return BaselineReport(
            stack_name=stack_name,
            baseline_label=baseline_label,
            diff=None,
            baseline_missing=True,
            issues=[f"No baseline snapshot found for label '{baseline_label}'"],
        )

    if current is None:
        return BaselineReport(
            stack_name=stack_name,
            baseline_label=baseline_label,
            diff=None,
            current_missing=True,
            issues=[f"Stack '{stack_name}' could not be fetched from AWS"],
        )

    diff = diff_stacks(baseline, current)

    if diff.status_diff:
        issues.append(
            f"Status changed: {diff.status_diff.old!r} -> {diff.status_diff.new!r}"
        )
    for key, fd in (diff.parameter_diff or {}).items():
        issues.append(f"Parameter '{key}' changed: {fd.old!r} -> {fd.new!r}")
    for key, fd in (diff.tag_diff or {}).items():
        issues.append(f"Tag '{key}' changed: {fd.old!r} -> {fd.new!r}")

    return BaselineReport(
        stack_name=stack_name,
        baseline_label=baseline_label,
        diff=diff,
        issues=issues,
    )


def format_baseline_report(report: BaselineReport, *, color: bool = True) -> str:
    """Render a BaselineReport as a human-readable string."""
    lines: List[str] = [
        f"Baseline: {report.baseline_label}  Stack: {report.stack_name}"
    ]

    if report.baseline_missing or report.current_missing:
        for issue in report.issues:
            lines.append(f"  ! {issue}")
        return "\n".join(lines)

    if not report.issues:
        lines.append("  ✓ No drift from baseline")
    else:
        lines.append(f"  {len(report.issues)} change(s) detected:")
        for issue in report.issues:
            lines.append(f"    • {issue}")

    return "\n".join(lines)
