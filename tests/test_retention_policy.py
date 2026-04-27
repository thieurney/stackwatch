"""Tests for stackwatch.retention_policy."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from stackwatch.retention_policy import (
    PruneResult,
    _parse_ts,
    prune_by_age,
    prune_by_count,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot(base: Path, stack: str, env: str, ts: str) -> Path:
    d = base / stack / env
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{stack}_{env}_{ts}.json"
    p.write_text(json.dumps({"status": "CREATE_COMPLETE", "ts": ts}))
    return p


TS_OLD = "2024-01-01T00:00:00"
TS_MID = "2024-06-01T00:00:00"
TS_NEW = "2024-12-01T00:00:00"


# ---------------------------------------------------------------------------
# _parse_ts
# ---------------------------------------------------------------------------

def test_parse_ts_valid():
    dt = _parse_ts(f"mystack_prod_{TS_NEW}.json")
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 12


def test_parse_ts_invalid_returns_none():
    assert _parse_ts("badfilename.json") is None


# ---------------------------------------------------------------------------
# prune_by_count
# ---------------------------------------------------------------------------

def test_prune_by_count_removes_oldest(tmp_path):
    for ts in [TS_OLD, TS_MID, TS_NEW]:
        _write_snapshot(tmp_path, "mystack", "prod", ts)

    result = prune_by_count("mystack", "prod", keep=2, snapshot_dir=str(tmp_path))

    assert result.removed_count == 1
    assert result.kept == 2
    assert TS_OLD in result.removed


def test_prune_by_count_keep_more_than_available(tmp_path):
    _write_snapshot(tmp_path, "mystack", "prod", TS_NEW)

    result = prune_by_count("mystack", "prod", keep=10, snapshot_dir=str(tmp_path))

    assert result.removed_count == 0
    assert result.kept == 1


def test_prune_by_count_removes_files_on_disk(tmp_path):
    p_old = _write_snapshot(tmp_path, "mystack", "prod", TS_OLD)
    _write_snapshot(tmp_path, "mystack", "prod", TS_NEW)

    prune_by_count("mystack", "prod", keep=1, snapshot_dir=str(tmp_path))

    assert not p_old.exists()


# ---------------------------------------------------------------------------
# prune_by_age
# ---------------------------------------------------------------------------

def test_prune_by_age_removes_old(tmp_path):
    _write_snapshot(tmp_path, "mystack", "prod", TS_OLD)
    _write_snapshot(tmp_path, "mystack", "prod", TS_NEW)

    now = datetime(2024, 12, 15, tzinfo=timezone.utc)
    result = prune_by_age("mystack", "prod", max_age_days=60, snapshot_dir=str(tmp_path), now=now)

    assert result.removed_count == 1
    assert TS_OLD in result.removed
    assert result.kept == 1


def test_prune_by_age_keeps_all_when_recent(tmp_path):
    _write_snapshot(tmp_path, "mystack", "prod", TS_NEW)

    now = datetime(2024, 12, 5, tzinfo=timezone.utc)
    result = prune_by_age("mystack", "prod", max_age_days=30, snapshot_dir=str(tmp_path), now=now)

    assert result.removed_count == 0
    assert result.kept == 1


def test_prune_result_dataclass():
    r = PruneResult(stack_name="s", environment="e", removed=["a", "b"], kept=3)
    assert r.removed_count == 2
