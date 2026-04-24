"""Compliance checking for CloudFormation stacks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState


@dataclass
class ComplianceRule:
    name: str
    description: str
    passed: bool
    detail: Optional[str] = None


@dataclass
class ComplianceReport:
    stack_name: str
    rules: List[ComplianceRule] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.rules if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.rules if not r.passed)

    @property
    def compliant(self) -> bool:
        return self.failed == 0


_TERMINAL_STATUSES = {"DELETE_FAILED", "ROLLBACK_FAILED", "UPDATE_ROLLBACK_FAILED"}
_REVIEW_STATUSES = {"REVIEW_IN_PROGRESS"}


def build_compliance_report(state: StackState) -> ComplianceReport:
    rules: List[ComplianceRule] = []

    # Rule 1: termination protection
    tp_enabled = state.raw.get("EnableTerminationProtection", False)
    rules.append(ComplianceRule(
        name="termination-protection",
        description="Termination protection should be enabled",
        passed=bool(tp_enabled),
        detail=None if tp_enabled else "EnableTerminationProtection is false",
    ))

    # Rule 2: stack not in a terminal failure state
    status = state.status or ""
    in_terminal = status in _TERMINAL_STATUSES
    rules.append(ComplianceRule(
        name="no-terminal-failure",
        description="Stack must not be in a terminal failure state",
        passed=not in_terminal,
        detail=f"Stack status is {status}" if in_terminal else None,
    ))

    # Rule 3: has at least one tag
    tags = state.raw.get("Tags", [])
    has_tags = len(tags) > 0
    rules.append(ComplianceRule(
        name="has-tags",
        description="Stack should have at least one tag",
        passed=has_tags,
        detail=None if has_tags else "No tags defined on stack",
    ))

    # Rule 4: description is present
    description = state.raw.get("Description", "")
    has_description = bool(description)
    rules.append(ComplianceRule(
        name="has-description",
        description="Stack should have a description",
        passed=has_description,
        detail=None if has_description else "Stack description is empty",
    ))

    return ComplianceReport(stack_name=state.name, rules=rules)


def format_compliance_report(report: ComplianceReport, *, color: bool = True, json_output: bool = False) -> str:
    if json_output:
        import json
        data = {
            "stack": report.stack_name,
            "compliant": report.compliant,
            "passed": report.passed,
            "failed": report.failed,
            "rules": [
                {"name": r.name, "passed": r.passed, "detail": r.detail}
                for r in report.rules
            ],
        }
        return json.dumps(data, indent=2)

    lines = [f"Compliance report for {report.stack_name}"]
    for rule in report.rules:
        icon = "\u2713" if rule.passed else "\u2717"
        if color:
            icon = ("\033[32m" + icon + "\033[0m") if rule.passed else ("\033[31m" + icon + "\033[0m")
        line = f"  {icon} {rule.name}: {rule.description}"
        if not rule.passed and rule.detail:
            line += f"\n      {rule.detail}"
        lines.append(line)
    summary = f"\nResult: {report.passed}/{len(report.rules)} rules passed"
    if color:
        colour_code = "\033[32m" if report.compliant else "\033[31m"
        summary = colour_code + summary + "\033[0m"
    lines.append(summary)
    return "\n".join(lines)
