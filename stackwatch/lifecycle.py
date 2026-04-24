"""Lifecycle analysis: creation date, last update, and age bucketing for a stack."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from stackwatch.fetcher import StackState


@dataclass
class LifecycleInfo:
    stack_name: str
    created_at: Optional[datetime]
    last_updated_at: Optional[datetime]
    age_days: Optional[int]
    update_age_days: Optional[int]
    age_bucket: str  # "new" | "active" | "mature" | "stale" | "unknown"


_BUCKETS = [
    (7, "new"),
    (30, "active"),
    (180, "mature"),
]


def _age_bucket(age_days: Optional[int]) -> str:
    if age_days is None:
        return "unknown"
    for threshold, label in _BUCKETS:
        if age_days <= threshold:
            return label
    return "stale"


def _days_since(dt: Optional[datetime]) -> Optional[int]:
    if dt is None:
        return None
    now = datetime.now(tz=timezone.utc)
    delta = now - dt.astimezone(timezone.utc)
    return max(0, delta.days)


def build_lifecycle(state: StackState) -> LifecycleInfo:
    """Derive lifecycle metadata from a StackState."""
    raw = state.raw or {}
    created_at: Optional[datetime] = raw.get("CreationTime")
    last_updated_at: Optional[datetime] = raw.get("LastUpdatedTime")

    age_days = _days_since(created_at)
    update_age_days = _days_since(last_updated_at)

    return LifecycleInfo(
        stack_name=state.name,
        created_at=created_at,
        last_updated_at=last_updated_at,
        age_days=age_days,
        update_age_days=update_age_days,
        age_bucket=_age_bucket(age_days),
    )


def format_lifecycle(info: LifecycleInfo, *, use_color: bool = True) -> str:
    """Return a human-readable summary of lifecycle info."""
    _BUCKET_COLORS = {
        "new": "\033[92m",
        "active": "\033[94m",
        "mature": "\033[93m",
        "stale": "\033[91m",
        "unknown": "\033[90m",
    }
    reset = "\033[0m" if use_color else ""

    def colorize(text: str, bucket: str) -> str:
        if not use_color:
            return text
        return f"{_BUCKET_COLORS.get(bucket, '')}{text}{reset}"

    created_str = info.created_at.strftime("%Y-%m-%d") if info.created_at else "unknown"
    updated_str = info.last_updated_at.strftime("%Y-%m-%d") if info.last_updated_at else "never"
    age_str = f"{info.age_days}d" if info.age_days is not None else "unknown"
    upd_age_str = f"{info.update_age_days}d" if info.update_age_days is not None else "n/a"

    bucket_label = colorize(info.age_bucket, info.age_bucket)
    lines = [
        f"Stack       : {info.stack_name}",
        f"Created     : {created_str}  (age: {age_str})",
        f"Last update : {updated_str}  (since: {upd_age_str})",
        f"Age bucket  : {bucket_label}",
    ]
    return "\n".join(lines)
