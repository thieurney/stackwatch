"""Snapshot retention policy: prune old snapshots based on age or count."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from stackwatch.snapshot import _snapshot_path, list_snapshots


@dataclass
class PruneResult:
    stack_name: str
    environment: str
    removed: List[str]
    kept: int

    @property
    def removed_count(self) -> int:
        return len(self.removed)


def _parse_ts(filename: str) -> Optional[datetime]:
    """Extract UTC datetime from snapshot filename '<stack>_<env>_<ts>.json'."""
    try:
        ts_part = filename.rsplit("_", 1)[-1].replace(".json", "")
        return datetime.fromisoformat(ts_part).replace(tzinfo=timezone.utc)
    except (ValueError, IndexError):
        return None


def prune_by_count(
    stack_name: str,
    environment: str,
    keep: int,
    snapshot_dir: str = ".stackwatch",
) -> PruneResult:
    """Keep only the *keep* most-recent snapshots; delete the rest."""
    snapshots = list_snapshots(stack_name, environment, snapshot_dir=snapshot_dir)
    snapshots_sorted = sorted(snapshots, reverse=True)  # ISO timestamps sort lexically
    to_remove = snapshots_sorted[keep:]
    removed_names: List[str] = []
    for ts in to_remove:
        path = _snapshot_path(stack_name, environment, ts, snapshot_dir=snapshot_dir)
        p = Path(path)
        if p.exists():
            p.unlink()
            removed_names.append(ts)
    return PruneResult(
        stack_name=stack_name,
        environment=environment,
        removed=removed_names,
        kept=len(snapshots_sorted) - len(removed_names),
    )


def prune_by_age(
    stack_name: str,
    environment: str,
    max_age_days: int,
    snapshot_dir: str = ".stackwatch",
    now: Optional[datetime] = None,
) -> PruneResult:
    """Delete snapshots older than *max_age_days* days."""
    if now is None:
        now = datetime.now(tz=timezone.utc)
    snapshots = list_snapshots(stack_name, environment, snapshot_dir=snapshot_dir)
    removed_names: List[str] = []
    kept = 0
    for ts in snapshots:
        snap_dt = _parse_ts(f"{stack_name}_{environment}_{ts}.json")
        if snap_dt is None:
            kept += 1
            continue
        age = (now - snap_dt).days
        if age > max_age_days:
            path = _snapshot_path(stack_name, environment, ts, snapshot_dir=snapshot_dir)
            p = Path(path)
            if p.exists():
                p.unlink()
            removed_names.append(ts)
        else:
            kept += 1
    return PruneResult(
        stack_name=stack_name,
        environment=environment,
        removed=removed_names,
        kept=kept,
    )
