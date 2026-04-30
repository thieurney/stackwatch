"""Budget awareness module: parse and summarise AWS Cost Explorer budget data for a stack."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetAlert:
    name: str
    limit_amount: float
    limit_unit: str
    actual_spend: float
    forecasted_spend: Optional[float]
    exceeded: bool

    @property
    def pct_used(self) -> Optional[float]:
        if self.limit_amount == 0:
            return None
        return round(self.actual_spend / self.limit_amount * 100, 1)


@dataclass
class BudgetReport:
    stack_name: str
    alerts: list[BudgetAlert] = field(default_factory=list)

    @property
    def has_exceeded(self) -> bool:
        return any(a.exceeded for a in self.alerts)

    @property
    def exceeded_count(self) -> int:
        return sum(1 for a in self.alerts if a.exceeded)


def _parse_alert(raw: dict) -> BudgetAlert:
    limit = raw.get("BudgetLimit", {})
    actual = raw.get("CalculatedSpend", {}).get("ActualSpend", {})
    forecasted = raw.get("CalculatedSpend", {}).get("ForecastedSpend", {})
    limit_amount = float(limit.get("Amount", 0))
    actual_amount = float(actual.get("Amount", 0))
    forecasted_amount = float(forecasted["Amount"]) if forecasted.get("Amount") else None
    exceeded = actual_amount > limit_amount
    return BudgetAlert(
        name=raw.get("BudgetName", "unknown"),
        limit_amount=limit_amount,
        limit_unit=limit.get("Unit", "USD"),
        actual_spend=actual_amount,
        forecasted_spend=forecasted_amount,
        exceeded=exceeded,
    )


def build_budget_report(stack_name: str, raw_budgets: list[dict]) -> BudgetReport:
    alerts = [_parse_alert(b) for b in raw_budgets]
    return BudgetReport(stack_name=stack_name, alerts=alerts)


def format_budget_report(report: BudgetReport, *, color: bool = False) -> str:
    if not report.alerts:
        return f"No budget data found for stack '{report.stack_name}'."
    lines = [f"Budget report for {report.stack_name}:"]
    for alert in report.alerts:
        pct = f"{alert.pct_used}%" if alert.pct_used is not None else "n/a"
        status = "EXCEEDED" if alert.exceeded else "OK"
        if color and alert.exceeded:
            status = f"\033[31m{status}\033[0m"
        elif color:
            status = f"\033[32m{status}\033[0m"
        forecast = f", forecast {alert.forecasted_spend:.2f}" if alert.forecasted_spend is not None else ""
        lines.append(
            f"  [{status}] {alert.name}: {alert.actual_spend:.2f}/{alert.limit_amount:.2f}"
            f" {alert.limit_unit} ({pct} used{forecast})"
        )
    return "\n".join(lines)
