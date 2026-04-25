"""Detect and report deprecated CloudFormation runtime features for a stack."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.fetcher import StackState

# Parameters whose names suggest deprecated or legacy usage
_DEPRECATED_PARAM_HINTS = [
    "LegacyMode",
    "OldVpc",
    "DeprecatedEndpoint",
]

# Stack statuses that indicate the stack itself is in a deprecated lifecycle
_DEPRECATED_STATUSES = {
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "DELETE_FAILED",
}


@dataclass
class DeprecationWarning:  # noqa: A001
    code: str
    message: str
    severity: str  # "high" | "medium" | "low"


@dataclass
class DeprecationReport:
    stack_name: str
    warnings: List[DeprecationWarning] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @property
    def high_count(self) -> int:
        return sum(1 for w in self.warnings if w.severity == "high")


def _check_status(state: StackState) -> List[DeprecationWarning]:
    if state.status in _DEPRECATED_STATUSES:
        return [
            DeprecationWarning(
                code="DEPRECATED_STATUS",
                message=f"Stack is in a deprecated terminal state: {state.status}",
                severity="high",
            )
        ]
    return []


def _check_parameters(state: StackState) -> List[DeprecationWarning]:
    warnings: List[DeprecationWarning] = []
    for param in state.parameters:
        for hint in _DEPRECATED_PARAM_HINTS:
            if hint.lower() in param.lower():
                warnings.append(
                    DeprecationWarning(
                        code="DEPRECATED_PARAM",
                        message=f"Parameter name suggests deprecated usage: {param}",
                        severity="medium",
                    )
                )
    return warnings


def _check_no_tags(state: StackState) -> List[DeprecationWarning]:
    if not state.tags:
        return [
            DeprecationWarning(
                code="NO_TAGS",
                message="Stack has no tags; tagging is required for modern governance.",
                severity="low",
            )
        ]
    return []


def build_deprecation_report(state: StackState) -> DeprecationReport:
    warnings: List[DeprecationWarning] = []
    warnings.extend(_check_status(state))
    warnings.extend(_check_parameters(state))
    warnings.extend(_check_no_tags(state))
    return DeprecationReport(stack_name=state.name, warnings=warnings)


def format_deprecation_report(report: DeprecationReport, *, color: bool = False) -> str:
    if not report.has_warnings:
        return f"Stack '{report.stack_name}': no deprecation warnings found."
    lines = [f"Stack '{report.stack_name}': {len(report.warnings)} deprecation warning(s)"]
    severity_color = {"high": "\033[31m", "medium": "\033[33m", "low": "\033[36m"}
    reset = "\033[0m"
    for w in report.warnings:
        prefix = f"[{w.severity.upper()}]"
        if color:
            c = severity_color.get(w.severity, "")
            prefix = f"{c}{prefix}{reset}"
        lines.append(f"  {prefix} {w.code}: {w.message}")
    return "\n".join(lines)
