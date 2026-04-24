"""Stack lineage: track creation time, age, and update history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class LineageEvent:
    timestamp: datetime
    status: str
    status_reason: Optional[str] = None


@dataclass
class StackLineage:
    stack_name: str
    created_at: Optional[datetime]
    last_updated_at: Optional[datetime]
    events: List[LineageEvent] = field(default_factory=list)

    @property
    def age_days(self) -> Optional[float]:
        if self.created_at is None:
            return None
        now = datetime.now(tz=timezone.utc)
        return (now - self.created_at).total_seconds() / 86400

    @property
    def update_count(self) -> int:
        return sum(
            1 for e in self.events
            if "UPDATE_COMPLETE" in e.status
        )


def build_lineage(stack_name: str, raw_events: List[dict]) -> StackLineage:
    """Build a StackLineage from raw CloudFormation event dicts."""
    events: List[LineageEvent] = [
        LineageEvent(
            timestamp=e["Timestamp"],
            status=e["ResourceStatus"],
            status_reason=e.get("ResourceStatusReason"),
        )
        for e in raw_events
        if e.get("ResourceType") == "AWS::CloudFormation::Stack"
    ]
    events.sort(key=lambda e: e.timestamp)

    created_at = events[0].timestamp if events else None
    last_updated_at = events[-1].timestamp if len(events) > 1 else None

    return StackLineage(
        stack_name=stack_name,
        created_at=created_at,
        last_updated_at=last_updated_at,
        events=events,
    )


def format_lineage(lineage: StackLineage, *, use_color: bool = True) -> str:
    """Return a human-readable summary of the stack lineage."""
    lines = [f"Stack: {lineage.stack_name}"]
    if lineage.created_at:
        lines.append(f"  Created     : {lineage.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    else:
        lines.append("  Created     : unknown")
    if lineage.age_days is not None:
        lines.append(f"  Age         : {lineage.age_days:.1f} days")
    if lineage.last_updated_at:
        lines.append(f"  Last updated: {lineage.last_updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"  Updates     : {lineage.update_count}")
    lines.append(f"  Total events: {len(lineage.events)}")
    return "\n".join(lines)
