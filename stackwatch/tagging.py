"""Tag compliance and analysis utilities for CloudFormation stacks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackwatch.fetcher import StackState


REQUIRED_TAGS: List[str] = ["Environment", "Owner", "Project"]


@dataclass
class TaggingIssue:
    key: str
    severity: str  # "high" | "medium" | "low"
    message: str


@dataclass
class TaggingReport:
    stack_name: str
    present: Dict[str, str] = field(default_factory=dict)
    issues: List[TaggingIssue] = field(default_factory=list)


def compliant(report: TaggingReport) -> bool:
    return not any(i.severity == "high" for i in report.issues)


def missing_required(report: TaggingReport) -> List[str]:
    return [i.key for i in report.issues if "missing" in i.message.lower()]


def build_tagging_report(
    state: StackState,
    required_keys: Optional[List[str]] = None,
) -> TaggingReport:
    keys = required_keys if required_keys is not None else REQUIRED_TAGS
    tags = dict(state.tags) if state.tags else {}
    issues: List[TaggingIssue] = []

    for key in keys:
        if key not in tags:
            issues.append(
                TaggingIssue(key=key, severity="high", message=f"Required tag '{key}' is missing")
            )

    for key, value in tags.items():
        if not value or not value.strip():
            issues.append(
                TaggingIssue(key=key, severity="medium", message=f"Tag '{key}' has an empty value")
            )

    if not tags:
        issues.append(
            TaggingIssue(key="*", severity="high", message="Stack has no tags at all")
        )

    return TaggingReport(stack_name=state.stack_name, present=tags, issues=issues)


def format_tagging_report(report: TaggingReport, *, color: bool = False, fmt: str = "plain") -> str:
    import json

    if fmt == "json":
        return json.dumps(
            {
                "stack": report.stack_name,
                "compliant": compliant(report),
                "tags": report.present,
                "issues": [{"key": i.key, "severity": i.severity, "message": i.message} for i in report.issues],
            },
            indent=2,
        )

    lines = [f"Stack: {report.stack_name}"]
    if report.present:
        lines.append("Tags:")
        for k, v in sorted(report.present.items()):
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (no tags)")

    if report.issues:
        lines.append("Issues:")
        for issue in report.issues:
            lines.append(f"  [{issue.severity.upper()}] {issue.message}")
    else:
        lines.append("No issues found.")

    return "\n".join(lines)
