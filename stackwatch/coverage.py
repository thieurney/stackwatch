"""Stack coverage analysis — checks which stacks have monitoring, tags, and protection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState


@dataclass
class CoverageGap:
    dimension: str
    detail: str
    severity: str  # "high" | "medium" | "low"


@dataclass
class CoverageReport:
    stack_name: str
    gaps: List[CoverageGap] = field(default_factory=list)
    score: int = 100


def covered(report: CoverageReport) -> bool:
    return not any(g.severity == "high" for g in report.gaps)


def gap_count(report: CoverageReport) -> int:
    return len(report.gaps)


def _check_termination_protection(state: StackState) -> Optional[CoverageGap]:
    if not state.raw.get("EnableTerminationProtection", False):
        return CoverageGap(
            dimension="termination_protection",
            detail="Termination protection is disabled",
            severity="high",
        )
    return None


def _check_tags(state: StackState) -> Optional[CoverageGap]:
    if not state.tags:
        return CoverageGap(
            dimension="tags",
            detail="Stack has no tags",
            severity="high",
        )
    return None


def _check_notification_arns(state: StackState) -> Optional[CoverageGap]:
    if not state.raw.get("NotificationARNs"):
        return CoverageGap(
            dimension="notifications",
            detail="No notification ARNs configured",
            severity="medium",
        )
    return None


def _check_description(state: StackState) -> Optional[CoverageGap]:
    if not state.raw.get("Description", "").strip():
        return CoverageGap(
            dimension="description",
            detail="Stack has no description",
            severity="low",
        )
    return None


_SEVERITY_WEIGHT = {"high": 30, "medium": 15, "low": 5}


def build_coverage_report(state: StackState) -> CoverageReport:
    checkers = [
        _check_termination_protection,
        _check_tags,
        _check_notification_arns,
        _check_description,
    ]
    gaps = [g for c in checkers if (g := c(state)) is not None]
    deduction = sum(_SEVERITY_WEIGHT.get(g.severity, 0) for g in gaps)
    score = max(0, 100 - deduction)
    return CoverageReport(stack_name=state.name, gaps=gaps, score=score)


def format_coverage_report(report: CoverageReport, *, color: bool = False) -> str:
    lines = [f"Coverage report for {report.stack_name}  (score: {report.score}/100)"]
    if not report.gaps:
        lines.append("  All coverage checks passed.")
    else:
        for gap in report.gaps:
            lines.append(f"  [{gap.severity.upper():6}] {gap.dimension}: {gap.detail}")
    return "\n".join(lines)
