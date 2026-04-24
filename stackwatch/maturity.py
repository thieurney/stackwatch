"""Stack maturity scoring based on operational best-practices."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.fetcher import StackState


@dataclass
class MaturityCheck:
    name: str
    passed: bool
    weight: int
    detail: str = ""


@dataclass
class MaturityReport:
    stack_name: str
    checks: List[MaturityCheck] = field(default_factory=list)
    score: int = 0
    grade: str = "F"


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def build_maturity_report(state: StackState) -> MaturityReport:
    checks: List[MaturityCheck] = []

    checks.append(MaturityCheck(
        name="termination_protection",
        passed=state.termination_protection,
        weight=20,
        detail="Termination protection should be enabled.",
    ))

    has_tags = bool(state.tags)
    checks.append(MaturityCheck(
        name="has_tags",
        passed=has_tags,
        weight=20,
        detail="Stack should have at least one tag.",
    ))

    non_failed = not state.status.endswith("_FAILED")
    checks.append(MaturityCheck(
        name="non_failed_status",
        passed=non_failed,
        weight=30,
        detail=f"Stack status is {state.status!r}; should not be a FAILED state.",
    ))

    has_desc = bool(state.description and state.description.strip())
    checks.append(MaturityCheck(
        name="has_description",
        passed=has_desc,
        weight=15,
        detail="Stack should have a non-empty description.",
    ))

    has_params = bool(state.parameters)
    checks.append(MaturityCheck(
        name="uses_parameters",
        passed=has_params,
        weight=15,
        detail="Stack should use parameters for configurability.",
    ))

    total_weight = sum(c.weight for c in checks)
    earned = sum(c.weight for c in checks if c.passed)
    score = int(earned * 100 / total_weight) if total_weight else 0

    return MaturityReport(
        stack_name=state.stack_name,
        checks=checks,
        score=score,
        grade=_grade(score),
    )


def format_maturity_report(report: MaturityReport, *, color: bool = True) -> str:
    GREEN = "\033[32m" if color else ""
    RED = "\033[31m" if color else ""
    RESET = "\033[0m" if color else ""

    lines = [
        f"Stack: {report.stack_name}",
        f"Maturity Score: {report.score}/100  Grade: {report.grade}",
        "",
    ]
    for c in report.checks:
        mark = f"{GREEN}PASS{RESET}" if c.passed else f"{RED}FAIL{RESET}"
        lines.append(f"  [{mark}] ({c.weight:2d}pts) {c.name}")
        if not c.passed:
            lines.append(f"          {c.detail}")
    return "\n".join(lines)
