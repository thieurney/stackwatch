"""Inventory module: collect and summarise multiple stacks into a flat report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from stackwatch.fetcher import StackState


@dataclass
class InventoryRow:
    stack_name: str
    status: str
    region: str
    parameter_count: int
    tag_count: int
    termination_protection: bool
    last_updated: Optional[str]


@dataclass
class InventoryReport:
    rows: List[InventoryRow] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def protected_count(self) -> int:
        return sum(1 for r in self.rows if r.termination_protection)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.rows if "FAILED" in r.status or "ROLLBACK" in r.status)


def _last_updated(state: StackState) -> Optional[str]:
    raw = state.raw or {}
    dt = raw.get("LastUpdatedTime") or raw.get("CreationTime")
    if dt is None:
        return None
    return str(dt)


def build_inventory(states: List[Optional[StackState]], region: str = "us-east-1") -> InventoryReport:
    """Build an InventoryReport from a list of fetched StackState objects.

    None entries (stacks that could not be fetched) are silently skipped.
    """
    rows: List[InventoryRow] = []
    for state in states:
        if state is None:
            continue
        raw = state.raw or {}
        row = InventoryRow(
            stack_name=state.stack_name,
            status=state.status,
            region=region,
            parameter_count=len(state.parameters),
            tag_count=len(state.tags),
            termination_protection=bool(raw.get("EnableTerminationProtection", False)),
            last_updated=_last_updated(state),
        )
        rows.append(row)
    return InventoryReport(rows=rows)


def format_inventory(report: InventoryReport, *, color: bool = False) -> str:
    """Return a plain-text table summarising the inventory."""
    if not report.rows:
        return "No stacks found."

    header = f"{'Stack':<40} {'Status':<28} {'Region':<15} {'Params':>6} {'Tags':>5} {'Protected':>9}"
    sep = "-" * len(header)
    lines = [header, sep]
    for r in report.rows:
        protected = "yes" if r.termination_protection else "no"
        lines.append(
            f"{r.stack_name:<40} {r.status:<28} {r.region:<15} {r.parameter_count:>6} {r.tag_count:>5} {protected:>9}"
        )
    lines.append(sep)
    lines.append(
        f"Total: {report.total}  Protected: {report.protected_count}  Failed/Rollback: {report.failed_count}"
    )
    return "\n".join(lines)
