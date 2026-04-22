"""Tests for stackwatch.health."""
import pytest
from stackwatch.health import (
    HealthIssue,
    HealthReport,
    build_health_report,
    format_health_report,
    _grade,
)


def test_grade_boundaries():
    assert _grade(100) == "A"
    assert _grade(90) == "A"
    assert _grade(89) == "B"
    assert _grade(80) == "B"
    assert _grade(79) == "C"
    assert _grade(60) == "C"
    assert _grade(59) == "D"
    assert _grade(40) == "D"
    assert _grade(39) == "F"
    assert _grade(0) == "F"


def test_healthy_stack_scores_100():
    report = build_health_report("CREATE_COMPLETE")
    assert report.score == 100
    assert report.grade == "A"
    assert report.healthy is True
    assert report.issues == []


def test_failed_status_deducts_50():
    report = build_health_report("UPDATE_FAILED")
    assert report.score == 50
    assert report.grade == "D"
    assert any(i.severity == "error" for i in report.issues)


def test_degraded_status_deducts_20():
    report = build_health_report("ROLLBACK_COMPLETE")
    assert report.score == 80
    assert report.grade == "B"


def test_drift_deducts_20():
    report = build_health_report("CREATE_COMPLETE", drifted=True)
    assert report.score == 80
    assert any("drift" in i.message.lower() for i in report.issues)


def test_alarms_deduct_up_to_20():
    report = build_health_report("CREATE_COMPLETE", alarm_count=10)
    assert report.score == 80  # capped at 20 deduction


def test_single_alarm_deducts_5():
    report = build_health_report("CREATE_COMPLETE", alarm_count=1)
    assert report.score == 95


def test_no_termination_protection_deducts_5():
    report = build_health_report("CREATE_COMPLETE", termination_protected=False)
    assert report.score == 95
    assert any(i.severity == "info" for i in report.issues)


def test_score_never_goes_below_zero():
    report = build_health_report(
        "UPDATE_FAILED", drifted=True, alarm_count=10, termination_protected=False
    )
    assert report.score == 0


def test_format_no_issues():
    report = HealthReport(score=100, grade="A", issues=[])
    text = format_health_report(report, color=False)
    assert "100/100" in text
    assert "No issues" in text


def test_format_with_issues():
    report = HealthReport(
        score=50,
        grade="D",
        issues=[HealthIssue("error", "Stack is in failed state: UPDATE_FAILED")],
    )
    text = format_health_report(report, color=False)
    assert "[ERR]" in text
    assert "UPDATE_FAILED" in text


def test_format_color_grade():
    report = HealthReport(score=100, grade="A", issues=[])
    text = format_health_report(report, color=True)
    assert "\033[92m" in text  # green for healthy
