"""Tests for stackwatch.stale."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from stackwatch.fetcher import StackState
from stackwatch.stale import (
    StalenessReport,
    StalenessWarning,
    _check_age,
    _check_last_update,
    _check_terminal_status,
    _days_since,
    build_staleness_report,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_state(
    status: str = "CREATE_COMPLETE",
    created_days_ago: float = 10,
    updated_days_ago: Optional[float] = None,
) -> StackState:
    creation = _now() - timedelta(days=created_days_ago)
    last_updated = (
        _now() - timedelta(days=updated_days_ago)
        if updated_days_ago is not None
        else None
    )
    return StackState(
        stack_name="my-stack",
        status=status,
        parameters={},
        tags={},
        outputs={},
        creation_time=creation,
        last_updated_time=last_updated,
        termination_protection=True,
    )


def test_days_since_returns_none_for_none():
    assert _days_since(None) is None


def test_days_since_approx():
    dt = _now() - timedelta(days=5)
    result = _days_since(dt)
    assert result is not None
    assert 4.9 < result < 5.1


def test_days_since_naive_datetime():
    naive = datetime.utcnow() - timedelta(days=3)
    result = _days_since(naive)
    assert result is not None
    assert 2.9 < result < 3.1


def test_check_age_below_threshold_returns_empty():
    state = _make_state(created_days_ago=10)
    assert _check_age(state, stale_days=90) == []


def test_check_age_above_threshold_returns_warning():
    state = _make_state(created_days_ago=100)
    warnings = _check_age(state, stale_days=90)
    assert len(warnings) == 1
    assert warnings[0].code == "OLD_STACK"
    assert warnings[0].severity == "medium"


def test_check_last_update_below_threshold_returns_empty():
    state = _make_state(updated_days_ago=5)
    assert _check_last_update(state, idle_days=30) == []


def test_check_last_update_above_threshold_returns_warning():
    state = _make_state(updated_days_ago=45)
    warnings = _check_last_update(state, idle_days=30)
    assert len(warnings) == 1
    assert warnings[0].code == "IDLE_STACK"
    assert warnings[0].severity == "low"


def test_check_terminal_status_clean_returns_empty():
    state = _make_state(status="CREATE_COMPLETE")
    assert _check_terminal_status(state) == []


def test_check_terminal_status_rollback_complete_is_high():
    state = _make_state(status="ROLLBACK_COMPLETE")
    warnings = _check_terminal_status(state)
    assert len(warnings) == 1
    assert warnings[0].code == "TERMINAL_STATUS"
    assert warnings[0].severity == "high"


def test_build_staleness_report_healthy_stack():
    state = _make_state(created_days_ago=5, updated_days_ago=2)
    report = build_staleness_report(state, stale_days=90, idle_days=30)
    assert not report.is_stale
    assert report.high_count == 0
    assert report.stack_name == "my-stack"


def test_build_staleness_report_stale_stack():
    state = _make_state(created_days_ago=100, updated_days_ago=50)
    report = build_staleness_report(state, stale_days=90, idle_days=30)
    assert report.is_stale
    codes = {w.code for w in report.warnings}
    assert "OLD_STACK" in codes
    assert "IDLE_STACK" in codes


def test_build_staleness_report_terminal_status_counts_high():
    state = _make_state(status="DELETE_FAILED", created_days_ago=5)
    report = build_staleness_report(state)
    assert report.high_count == 1
