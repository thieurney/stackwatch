"""Detect stale CloudFormation stacks based on age and activity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from stackwatch.fetcher import StackState

_STALE_DAYS_DEFAULT = 90
_IDLE_DAYS_DEFAULT = 30


@dataclass
class StalenessWarning:
    code: str
    severity: str  # "high" | "medium" | "low"
    message: str


@dataclass
class StalenessReport:
    stack_name: str
    age_days: Optional[float]
    last_updated_days: Optional[float]
    warnings: List[StalenessWarning] = field(default_factory=list)

    @property
    def is_stale(self) -> bool:
        return bool(self.warnings)

    @property
    def high_count(self) -> int:
        return sum(1 for w in self.warnings if w.severity == "high")


def _days_since(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400


def _check_age(
    state: StackState, stale_days: int
) -> List[StalenessWarning]:
    warnings: List[StalenessWarning] = []
    age = _days_since(state.creation_time)
    if age is not None and age > stale_days:
        warnings.append(
            StalenessWarning(
                code="OLD_STACK",
                severity="medium",
                message=f"Stack is {age:.0f} days old (threshold: {stale_days}d).",
            )
        )
    return warnings


def _check_last_update(
    state: StackState, idle_days: int
) -> List[StalenessWarning]:
    warnings: List[StalenessWarning] = []
    last = state.last_updated_time or state.creation_time
    idle = _days_since(last)
    if idle is not None and idle > idle_days:
        warnings.append(
            StalenessWarning(
                code="IDLE_STACK",
                severity="low",
                message=f"Stack has not been updated in {idle:.0f} days (threshold: {idle_days}d).",
            )
        )
    return warnings


def _check_terminal_status(state: StackState) -> List[StalenessWarning]:
    terminal = {"ROLLBACK_COMPLETE", "DELETE_FAILED", "UPDATE_ROLLBACK_FAILED"}
    if state.status in terminal:
        return [
            StalenessWarning(
                code="TERMINAL_STATUS",
                severity="high",
                message=f"Stack is in terminal status '{state.status}' and may be abandoned.",
            )
        ]
    return []


def build_staleness_report(
    state: StackState,
    stale_days: int = _STALE_DAYS_DEFAULT,
    idle_days: int = _IDLE_DAYS_DEFAULT,
) -> StalenessReport:
    warnings: List[StalenessWarning] = []
    warnings.extend(_check_terminal_status(state))
    warnings.extend(_check_age(state, stale_days))
    warnings.extend(_check_last_update(state, idle_days))
    return StalenessReport(
        stack_name=state.stack_name,
        age_days=_days_since(state.creation_time),
        last_updated_days=_days_since(state.last_updated_time or state.creation_time),
        warnings=warnings,
    )
