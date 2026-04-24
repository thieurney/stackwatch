"""Tests for stackwatch.lifecycle."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.fetcher import StackState
from stackwatch.lifecycle import (
    LifecycleInfo,
    _age_bucket,
    _days_since,
    build_lifecycle,
    format_lifecycle,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_state(
    created_days_ago: int | None = None,
    updated_days_ago: int | None = None,
) -> StackState:
    raw: dict = {}
    if created_days_ago is not None:
        raw["CreationTime"] = _now() - timedelta(days=created_days_ago)
    if updated_days_ago is not None:
        raw["LastUpdatedTime"] = _now() - timedelta(days=updated_days_ago)
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs=[],
        raw=raw,
    )


# ---------------------------------------------------------------------------
# _age_bucket
# ---------------------------------------------------------------------------

def test_age_bucket_none_returns_unknown():
    assert _age_bucket(None) == "unknown"


def test_age_bucket_new():
    assert _age_bucket(3) == "new"


def test_age_bucket_boundary_new():
    assert _age_bucket(7) == "new"


def test_age_bucket_active():
    assert _age_bucket(15) == "active"


def test_age_bucket_mature():
    assert _age_bucket(90) == "mature"


def test_age_bucket_stale():
    assert _age_bucket(200) == "stale"


# ---------------------------------------------------------------------------
# _days_since
# ---------------------------------------------------------------------------

def test_days_since_none_returns_none():
    assert _days_since(None) is None


def test_days_since_today_returns_zero():
    assert _days_since(_now()) == 0


def test_days_since_five_days_ago():
    dt = _now() - timedelta(days=5)
    assert _days_since(dt) == 5


# ---------------------------------------------------------------------------
# build_lifecycle
# ---------------------------------------------------------------------------

def test_build_lifecycle_no_dates():
    state = _make_state()
    info = build_lifecycle(state)
    assert info.stack_name == "my-stack"
    assert info.created_at is None
    assert info.age_days is None
    assert info.age_bucket == "unknown"


def test_build_lifecycle_with_dates():
    state = _make_state(created_days_ago=10, updated_days_ago=2)
    info = build_lifecycle(state)
    assert info.age_days == 10
    assert info.update_age_days == 2
    assert info.age_bucket == "active"


# ---------------------------------------------------------------------------
# format_lifecycle
# ---------------------------------------------------------------------------

def test_format_lifecycle_contains_stack_name():
    state = _make_state(created_days_ago=5)
    info = build_lifecycle(state)
    output = format_lifecycle(info, use_color=False)
    assert "my-stack" in output
    assert "new" in output


def test_format_lifecycle_no_color_no_escape():
    state = _make_state(created_days_ago=300)
    info = build_lifecycle(state)
    output = format_lifecycle(info, use_color=False)
    assert "\033[" not in output
    assert "stale" in output


def test_format_lifecycle_with_color_has_escape():
    state = _make_state(created_days_ago=3)
    info = build_lifecycle(state)
    output = format_lifecycle(info, use_color=True)
    assert "\033[" in output
