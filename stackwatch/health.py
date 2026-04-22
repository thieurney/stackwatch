"""Stack health scoring based on status, drift, and alarm state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Statuses considered unhealthy
_FAILED_STATUSES = {
    "CREATE_FAILED",
    "ROLLBACK_FAILED",
    "DELETE_FAILED",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
    "IMPORT_ROLLBACK_FAILED",
}

_DEGRADED_STATUSES = {
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_ROLLBACK_COMPLETE",
}


@dataclass
class HealthIssue:
    severity: str  # "error" | "warning" | "info"
    message: str


@dataclass
class HealthReport:
    score: int  # 0-100
    grade: str  # A / B / C / D / F
    issues: List[HealthIssue] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.score >= 80


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def build_health_report(
    status: str,
    drifted: bool = False,
    alarm_count: int = 0,
    termination_protected: bool = True,
) -> HealthReport:
    """Compute a health score from stack attributes."""
    score = 100
    issues: List[HealthIssue] = []

    if status in _FAILED_STATUSES:
        score -= 50
        issues.append(HealthIssue("error", f"Stack is in failed state: {status}"))
    elif status in _DEGRADED_STATUSES:
        score -= 20
        issues.append(HealthIssue("warning", f"Stack is in degraded state: {status}"))

    if drifted:
        score -= 20
        issues.append(HealthIssue("warning", "Stack has drifted resources"))

    if alarm_count > 0:
        deduction = min(20, alarm_count * 5)
        score -= deduction
        issues.append(HealthIssue("error", f"{alarm_count} CloudWatch alarm(s) in ALARM state"))

    if not termination_protected:
        score -= 5
        issues.append(HealthIssue("info", "Termination protection is disabled"))

    score = max(0, score)
    return HealthReport(score=score, grade=_grade(score), issues=issues)


def format_health_report(report: HealthReport, *, color: bool = True) -> str:
    """Return a human-readable health summary."""
    lines = []
    grade_str = report.grade
    if color:
        code = "\033[92m" if report.healthy else "\033[91m"
        grade_str = f"{code}{report.grade}\033[0m"
    lines.append(f"Health score : {report.score}/100  (grade {grade_str})")
    if not report.issues:
        lines.append("  No issues detected.")
    else:
        for issue in report.issues:
            prefix = {"error": "[ERR]", "warning": "[WRN]", "info": "[INF]"}.get(issue.severity, "[?]")
            lines.append(f"  {prefix} {issue.message}")
    return "\n".join(lines)
