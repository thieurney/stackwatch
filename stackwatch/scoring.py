"""Aggregate scoring module for CloudFormation stacks.

Combines health, maturity, compliance, and anomaly signals into a single
normalised score (0–100) with a letter grade and per-dimension breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState
from stackwatch.health import build_health_report
from stackwatch.maturity import build_maturity_report
from stackwatch.compliance import build_compliance_report
from stackwatch.anomaly import build_anomaly_report


# ---------------------------------------------------------------------------
# Weights (must sum to 1.0)
# ---------------------------------------------------------------------------
_WEIGHT_HEALTH = 0.35
_WEIGHT_MATURITY = 0.25
_WEIGHT_COMPLIANCE = 0.25
_WEIGHT_ANOMALY = 0.15


@dataclass
class DimensionScore:
    """Score for a single dimension contributing to the aggregate."""

    name: str
    score: int          # 0-100
    weight: float       # contribution weight
    notes: List[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        """Weighted contribution to the aggregate score."""
        return self.score * self.weight


@dataclass
class AggregateScore:
    """Full aggregate score for a single stack."""

    stack_name: str
    total: int                          # 0-100 rounded
    grade: str                          # A-F
    dimensions: List[DimensionScore] = field(default_factory=list)


def _grade(score: int) -> str:
    """Convert a 0-100 integer score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _anomaly_score(state: StackState) -> tuple[int, List[str]]:
    """Derive a 0-100 score from the anomaly report (fewer anomalies = higher score)."""
    report = build_anomaly_report(state)
    notes: List[str] = [f.message for f in report.findings]

    # Deduct points: high=30, medium=15, low=5 (capped at 0)
    deduction = report.high_count * 30 + report.medium_count * 15
    deduction += len([f for f in report.findings if f.severity == "low"]) * 5
    return max(0, 100 - deduction), notes


def build_aggregate_score(state: Optional[StackState]) -> Optional[AggregateScore]:
    """Build an AggregateScore for *state*.

    Returns ``None`` when *state* is ``None`` (stack not found).
    """
    if state is None:
        return None

    # --- Health dimension ---------------------------------------------------
    health = build_health_report(state)
    health_dim = DimensionScore(
        name="health",
        score=health.score,
        weight=_WEIGHT_HEALTH,
        notes=[i.message for i in health.issues],
    )

    # --- Maturity dimension -------------------------------------------------
    maturity = build_maturity_report(state)
    maturity_dim = DimensionScore(
        name="maturity",
        score=maturity.score,
        weight=_WEIGHT_MATURITY,
        notes=[c.message for c in maturity.checks if not c.passed],
    )

    # --- Compliance dimension -----------------------------------------------
    compliance = build_compliance_report(state)
    compliance_dim = DimensionScore(
        name="compliance",
        score=compliance.score,
        weight=_WEIGHT_COMPLIANCE,
        notes=[r.message for r in compliance.rules if not r.passed],
    )

    # --- Anomaly dimension --------------------------------------------------
    anomaly_raw, anomaly_notes = _anomaly_score(state)
    anomaly_dim = DimensionScore(
        name="anomaly",
        score=anomaly_raw,
        weight=_WEIGHT_ANOMALY,
        notes=anomaly_notes,
    )

    # --- Aggregate ----------------------------------------------------------
    dimensions = [health_dim, maturity_dim, compliance_dim, anomaly_dim]
    total = round(sum(d.weighted for d in dimensions))
    total = max(0, min(100, total))

    return AggregateScore(
        stack_name=state.name,
        total=total,
        grade=_grade(total),
        dimensions=dimensions,
    )


def format_aggregate_score(agg: AggregateScore, *, color: bool = True) -> str:
    """Return a human-readable summary of *agg*."""
    _RESET = "\033[0m" if color else ""
    _BOLD = "\033[1m" if color else ""

    grade_colors = {
        "A": "\033[32m",   # green
        "B": "\033[36m",   # cyan
        "C": "\033[33m",   # yellow
        "D": "\033[35m",   # magenta
        "F": "\033[31m",   # red
    }
    gc = grade_colors.get(agg.grade, "") if color else ""

    lines = [
        f"{_BOLD}Stack:{_RESET} {agg.stack_name}",
        f"{_BOLD}Score:{_RESET} {gc}{agg.total}/100  [{agg.grade}]{_RESET}",
        "",
        f"{_BOLD}Dimensions:{_RESET}",
    ]
    for dim in agg.dimensions:
        pct = f"{dim.score:>3}/100"
        lines.append(f"  {dim.name:<12} {pct}  (weight {dim.weight:.0%})")
        for note in dim.notes:
            lines.append(f"    · {note}")

    return "\n".join(lines)
