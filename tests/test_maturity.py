"""Tests for stackwatch.maturity."""
from stackwatch.fetcher import StackState
from stackwatch.maturity import (
    MaturityReport,
    build_maturity_report,
    format_maturity_report,
    _grade,
)


def _make_state(**kwargs) -> StackState:
    defaults = dict(
        stack_name="my-stack",
        status="CREATE_COMPLETE",
        parameters={"Env": "prod"},
        outputs={},
        tags={"Owner": "team"},
        description="A test stack.",
        termination_protection=True,
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def test_grade_boundaries():
    assert _grade(100) == "A"
    assert _grade(90) == "A"
    assert _grade(89) == "B"
    assert _grade(75) == "B"
    assert _grade(74) == "C"
    assert _grade(60) == "C"
    assert _grade(59) == "D"
    assert _grade(40) == "D"
    assert _grade(39) == "F"
    assert _grade(0) == "F"


def test_fully_mature_stack_scores_100():
    state = _make_state()
    report = build_maturity_report(state)
    assert report.score == 100
    assert report.grade == "A"
    assert all(c.passed for c in report.checks)


def test_no_termination_protection_deducts_weight():
    state = _make_state(termination_protection=False)
    report = build_maturity_report(state)
    assert report.score < 100
    failed = [c for c in report.checks if not c.passed]
    assert any(c.name == "termination_protection" for c in failed)


def test_no_tags_fails_check():
    state = _make_state(tags={})
    report = build_maturity_report(state)
    failed_names = {c.name for c in report.checks if not c.passed}
    assert "has_tags" in failed_names


def test_failed_status_fails_check():
    state = _make_state(status="UPDATE_ROLLBACK_FAILED")
    report = build_maturity_report(state)
    failed_names = {c.name for c in report.checks if not c.passed}
    assert "non_failed_status" in failed_names


def test_no_description_fails_check():
    state = _make_state(description="")
    report = build_maturity_report(state)
    failed_names = {c.name for c in report.checks if not c.passed}
    assert "has_description" in failed_names


def test_no_parameters_fails_check():
    state = _make_state(parameters={})
    report = build_maturity_report(state)
    failed_names = {c.name for c in report.checks if not c.passed}
    assert "uses_parameters" in failed_names


def test_format_includes_score_and_grade():
    state = _make_state()
    report = build_maturity_report(state)
    output = format_maturity_report(report, color=False)
    assert "100/100" in output
    assert "Grade: A" in output


def test_format_shows_fail_detail_for_failing_checks():
    state = _make_state(termination_protection=False, tags={})
    report = build_maturity_report(state)
    output = format_maturity_report(report, color=False)
    assert "FAIL" in output
    assert "termination_protection" in output
    assert "has_tags" in output


def test_report_stack_name_preserved():
    state = _make_state(stack_name="prod-api")
    report = build_maturity_report(state)
    assert report.stack_name == "prod-api"
