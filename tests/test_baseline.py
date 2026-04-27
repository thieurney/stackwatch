"""Tests for stackwatch.baseline."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytest

from stackwatch.fetcher import StackState
from stackwatch.baseline import (
    BaselineReport,
    build_baseline_report,
    drifted_from_baseline,
    format_baseline_report,
)


def _make_state(
    status: str = "UPDATE_COMPLETE",
    parameters: Optional[dict] = None,
    tags: Optional[dict] = None,
) -> StackState:
    return StackState(
        name="my-stack",
        status=status,
        parameters=parameters or {"Env": "prod"},
        tags=tags or {"team": "platform"},
        outputs={},
        creation_time=datetime(2024, 1, 1),
        last_updated=datetime(2024, 6, 1),
    )


# ---------------------------------------------------------------------------
# drifted_from_baseline
# ---------------------------------------------------------------------------

def test_drifted_when_baseline_missing():
    report = BaselineReport(
        stack_name="s", baseline_label="v1", diff=None, baseline_missing=True
    )
    assert drifted_from_baseline(report) is True


def test_drifted_when_current_missing():
    report = BaselineReport(
        stack_name="s", baseline_label="v1", diff=None, current_missing=True
    )
    assert drifted_from_baseline(report) is True


def test_not_drifted_when_identical():
    state = _make_state()
    report = build_baseline_report("my-stack", "v1", state, state)
    assert drifted_from_baseline(report) is False


def test_drifted_when_status_changed():
    baseline = _make_state(status="UPDATE_COMPLETE")
    current = _make_state(status="ROLLBACK_COMPLETE")
    report = build_baseline_report("my-stack", "v1", baseline, current)
    assert drifted_from_baseline(report) is True


# ---------------------------------------------------------------------------
# build_baseline_report
# ---------------------------------------------------------------------------

def test_report_baseline_missing():
    report = build_baseline_report("my-stack", "v1", None, _make_state())
    assert report.baseline_missing is True
    assert any("v1" in i for i in report.issues)


def test_report_current_missing():
    report = build_baseline_report("my-stack", "v1", _make_state(), None)
    assert report.current_missing is True
    assert any("my-stack" in i for i in report.issues)


def test_report_no_changes():
    state = _make_state()
    report = build_baseline_report("my-stack", "v1", state, state)
    assert report.issues == []
    assert report.diff is not None


def test_report_parameter_change_creates_issue():
    baseline = _make_state(parameters={"Env": "prod"})
    current = _make_state(parameters={"Env": "staging"})
    report = build_baseline_report("my-stack", "v1", baseline, current)
    assert any("Env" in i for i in report.issues)


# ---------------------------------------------------------------------------
# format_baseline_report
# ---------------------------------------------------------------------------

def test_format_no_drift():
    state = _make_state()
    report = build_baseline_report("my-stack", "v1", state, state)
    output = format_baseline_report(report, color=False)
    assert "No drift" in output


def test_format_with_changes():
    baseline = _make_state(status="UPDATE_COMPLETE")
    current = _make_state(status="ROLLBACK_COMPLETE")
    report = build_baseline_report("my-stack", "v1", baseline, current)
    output = format_baseline_report(report, color=False)
    assert "change(s) detected" in output
    assert "Status changed" in output


def test_format_missing_baseline():
    report = build_baseline_report("my-stack", "v1", None, _make_state())
    output = format_baseline_report(report, color=False)
    assert "v1" in output
