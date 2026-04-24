"""Aggregate multi-stack summary rolled up into a single report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState


@dataclass
class StackRollupRow:
    name: str
    status: str
    region: str
    parameter_count: int
    tag_count: int
    drift_status: Optional[str]


@dataclass
class RollupReport:
    rows: List[StackRollupRow] = field(default_factory=list)
    total: int = 0
    healthy: int = 0
    failed: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.failed / self.total * 100, 1)


_FAILED_SUFFIXES = ("FAILED", "ROLLBACK_COMPLETE", "ROLLBACK_FAILED")


def _is_failed(status: str) -> bool:
    return any(status.endswith(s) for s in _FAILED_SUFFIXES)


def build_rollup(states: List[StackState]) -> RollupReport:
    rows: List[StackRollupRow] = []
    healthy = 0
    failed = 0

    for state in states:
        row = StackRollupRow(
            name=state.name,
            status=state.status,
            region=state.region,
            parameter_count=len(state.parameters),
            tag_count=len(state.tags),
            drift_status=state.raw.get("DriftInformation", {}).get("StackDriftStatus"),
        )
        rows.append(row)
        if _is_failed(state.status):
            failed += 1
        else:
            healthy += 1

    return RollupReport(rows=rows, total=len(states), healthy=healthy, failed=failed)


def format_rollup(report: RollupReport, *, color: bool = True, fmt: str = "plain") -> str:
    import json

    if fmt == "json":
        return json.dumps(
            {
                "total": report.total,
                "healthy": report.healthy,
                "failed": report.failed,
                "failure_rate_pct": report.failure_rate,
                "stacks": [
                    {
                        "name": r.name,
                        "status": r.status,
                        "region": r.region,
                        "parameters": r.parameter_count,
                        "tags": r.tag_count,
                        "drift": r.drift_status,
                    }
                    for r in report.rows
                ],
            },
            indent=2,
        )

    lines = [f"Stacks: {report.total}  Healthy: {report.healthy}  Failed: {report.failed}  ({report.failure_rate}% failure rate)"]
    lines.append(f"{'Name':<40} {'Status':<30} {'Region':<15} {'Params':>6} {'Tags':>5} {'Drift':<15}")
    lines.append("-" * 115)
    for r in report.rows:
        drift = r.drift_status or "N/A"
        lines.append(f"{r.name:<40} {r.status:<30} {r.region:<15} {r.parameter_count:>6} {r.tag_count:>5} {drift:<15}")
    return "\n".join(lines)
