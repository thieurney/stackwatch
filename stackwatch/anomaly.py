"""Detect anomalies in CloudFormation stack state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from stackwatch.fetcher import StackState

_TERMINAL_STATUSES = {
    "CREATE_FAILED",
    "ROLLBACK_FAILED",
    "DELETE_FAILED",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
    "ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
}

_LONG_RUNNING_THRESHOLD_DAYS = 365


@dataclass
class AnomalyFinding:
    severity: str  # "high" | "medium" | "low"
    code: str
    message: str


@dataclass
class AnomalyReport:
    stack_name: str
    findings: List[AnomalyFinding] = field(default_factory=list)

    @property
    def has_anomalies(self) -> bool:
        return bool(self.findings)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "medium")


def _check_status(state: StackState) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    if state.status in _TERMINAL_STATUSES:
        findings.append(
            AnomalyFinding(
                severity="high",
                code="TERMINAL_STATUS",
                message=f"Stack is in terminal status: {state.status}",
            )
        )
    return findings


def _check_no_tags(state: StackState) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    if not state.tags:
        findings.append(
            AnomalyFinding(
                severity="low",
                code="NO_TAGS",
                message="Stack has no tags; consider adding environment/owner tags.",
            )
        )
    return findings


def _check_no_parameters(state: StackState) -> List[AnomalyFinding]:
    findings: List[AnomalyFinding] = []
    if not state.parameters:
        findings.append(
            AnomalyFinding(
                severity="low",
                code="NO_PARAMETERS",
                message="Stack has no parameters; template may be hardcoded.",
            )
        )
    return findings


def build_anomaly_report(state: StackState) -> AnomalyReport:
    findings: List[AnomalyFinding] = []
    findings.extend(_check_status(state))
    findings.extend(_check_no_tags(state))
    findings.extend(_check_no_parameters(state))
    return AnomalyReport(stack_name=state.stack_name, findings=findings)


def format_anomaly_report(report: AnomalyReport, *, color: bool = True) -> str:
    if not report.has_anomalies:
        return f"[{report.stack_name}] No anomalies detected."
    lines = [f"[{report.stack_name}] {len(report.findings)} anomaly(ies) found:"]
    for f in report.findings:
        prefix = f"  [{f.severity.upper()}] {f.code}:"
        lines.append(f"{prefix} {f.message}")
    return "\n".join(lines)
