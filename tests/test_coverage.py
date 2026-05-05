"""Tests for stackwatch.coverage."""
from __future__ import annotations

from stackwatch.coverage import (
    build_coverage_report,
    covered,
    format_coverage_report,
    gap_count,
)
from stackwatch.fetcher import StackState


def _make_state(
    name: str = "my-stack",
    status: str = "UPDATE_COMPLETE",
    tags: dict | None = None,
    termination: bool = True,
    notifications: list | None = None,
    description: str = "A stack",
) -> StackState:
    raw = {
        "StackName": name,
        "StackStatus": status,
        "EnableTerminationProtection": termination,
        "NotificationARNs": notifications or [],
        "Description": description,
    }
    return StackState(
        name=name,
        status=status,
        parameters={},
        tags=tags if tags is not None else {"env": "prod"},
        raw=raw,
    )


def test_fully_covered_stack_scores_100():
    state = _make_state(notifications=["arn:aws:sns:us-east-1:123:alerts"])
    report = build_coverage_report(state)
    assert report.score == 100
    assert gap_count(report) == 0
    assert covered(report)


def test_no_termination_protection_deducts_30():
    state = _make_state(termination=False, notifications=["arn:aws:sns:us-east-1:123:x"])
    report = build_coverage_report(state)
    assert report.score == 70
    assert any(g.dimension == "termination_protection" for g in report.gaps)
    assert not covered(report)


def test_no_tags_deducts_30():
    state = _make_state(tags={}, notifications=["arn:aws:sns:us-east-1:123:x"])
    report = build_coverage_report(state)
    assert report.score == 70
    assert any(g.dimension == "tags" for g in report.gaps)


def test_no_notifications_deducts_15():
    state = _make_state(notifications=[])
    report = build_coverage_report(state)
    assert report.score == 85
    assert any(g.dimension == "notifications" for g in report.gaps)


def test_no_description_deducts_5():
    state = _make_state(description="", notifications=["arn:aws:sns:us-east-1:123:x"])
    report = build_coverage_report(state)
    assert report.score == 95
    assert any(g.dimension == "description" for g in report.gaps)


def test_score_floor_is_zero():
    state = _make_state(termination=False, tags={}, notifications=[], description="")
    report = build_coverage_report(state)
    assert report.score == 0


def test_format_no_gaps():
    state = _make_state(notifications=["arn:x"])
    report = build_coverage_report(state)
    text = format_coverage_report(report)
    assert "All coverage checks passed" in text
    assert "100/100" in text


def test_format_with_gaps():
    state = _make_state(termination=False, tags={}, notifications=[])
    report = build_coverage_report(state)
    text = format_coverage_report(report)
    assert "termination_protection" in text
    assert "tags" in text
    assert "notifications" in text
