"""Parse and format CloudWatch alarm associations for a CloudFormation stack."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StackAlarm:
    name: str
    state: str
    metric: str
    namespace: str
    threshold: float | None = None
    comparison: str = ""


@dataclass
class AlarmSummary:
    alarms: list[StackAlarm] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for a in self.alarms if a.state == "OK")

    @property
    def alarm_count(self) -> int:
        return sum(1 for a in self.alarms if a.state == "ALARM")

    @property
    def insufficient_count(self) -> int:
        return sum(1 for a in self.alarms if a.state == "INSUFFICIENT_DATA")


def parse_alarm(raw: dict[str, Any]) -> StackAlarm:
    metrics = raw.get("Metrics", [])
    metric_name = raw.get("MetricName", "")
    namespace = raw.get("Namespace", "")
    if not metric_name and metrics:
        first = metrics[0].get("MetricStat", {}).get("Metric", {})
        metric_name = first.get("MetricName", "")
        namespace = first.get("Namespace", "")
    return StackAlarm(
        name=raw.get("AlarmName", ""),
        state=raw.get("StateValue", "UNKNOWN"),
        metric=metric_name,
        namespace=namespace,
        threshold=raw.get("Threshold"),
        comparison=raw.get("ComparisonOperator", ""),
    )


def format_alarm_summary(summary: AlarmSummary, *, color: bool = True, fmt: str = "plain") -> str:
    import json

    if fmt == "json":
        return json.dumps(
            [
                {
                    "name": a.name,
                    "state": a.state,
                    "metric": a.metric,
                    "namespace": a.namespace,
                    "threshold": a.threshold,
                    "comparison": a.comparison,
                }
                for a in summary.alarms
            ],
            indent=2,
        )

    if not summary.alarms:
        return "No alarms associated with this stack."

    _STATE_COLOR = {"OK": "\033[32m", "ALARM": "\033[31m", "INSUFFICIENT_DATA": "\033[33m"}
    _RESET = "\033[0m"
    lines = []
    for a in summary.alarms:
        state_str = a.state
        if color:
            c = _STATE_COLOR.get(a.state, "")
            state_str = f"{c}{a.state}{_RESET}" if c else a.state
        threshold_str = f" (threshold={a.threshold}" + (f" {a.comparison})" if a.comparison else ")") if a.threshold is not None else ""
        lines.append(f"  {a.name:<45} {state_str}  {a.namespace}/{a.metric}{threshold_str}")
    header = f"Alarms: {summary.alarm_count} ALARM, {summary.ok_count} OK, {summary.insufficient_count} INSUFFICIENT_DATA"
    return "\n".join([header] + lines)
