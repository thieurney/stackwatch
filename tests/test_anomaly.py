"""Tests for stackwatch.anomaly."""
from stackwatch.fetcher import StackState
from stackwatch.anomaly import (
    AnomalyFinding,
    AnomalyReport,
    _check_status,
    _check_no_tags,
    _check_no_parameters,
    build_anomaly_report,
    format_anomaly_report,
)


def _make_state(**kwargs) -> StackState:
    defaults = dict(
        stack_name="my-stack",
        status="CREATE_COMPLETE",
        parameters={"Env": "prod"},
        outputs={},
        tags={"Owner": "team"},
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def test_check_status_clean_returns_empty():
    state = _make_state(status="CREATE_COMPLETE")
    assert _check_status(state) == []


def test_check_status_terminal_returns_high():
    state = _make_state(status="ROLLBACK_COMPLETE")
    findings = _check_status(state)
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].code == "TERMINAL_STATUS"
    assert "ROLLBACK_COMPLETE" in findings[0].message


def test_check_no_tags_with_tags_returns_empty():
    state = _make_state(tags={"Env": "prod"})
    assert _check_no_tags(state) == []


def test_check_no_tags_empty_tags_returns_low():
    state = _make_state(tags={})
    findings = _check_no_tags(state)
    assert len(findings) == 1
    assert findings[0].severity == "low"
    assert findings[0].code == "NO_TAGS"


def test_check_no_parameters_with_params_returns_empty():
    state = _make_state(parameters={"Key": "Val"})
    assert _check_no_parameters(state) == []


def test_check_no_parameters_empty_returns_low():
    state = _make_state(parameters={})
    findings = _check_no_parameters(state)
    assert len(findings) == 1
    assert findings[0].severity == "low"
    assert findings[0].code == "NO_PARAMETERS"


def test_build_anomaly_report_clean_stack():
    state = _make_state()
    report = build_anomaly_report(state)
    assert report.stack_name == "my-stack"
    assert not report.has_anomalies
    assert report.high_count == 0
    assert report.medium_count == 0


def test_build_anomaly_report_multiple_issues():
    state = _make_state(status="DELETE_FAILED", tags={}, parameters={})
    report = build_anomaly_report(state)
    assert report.has_anomalies
    assert report.high_count == 1
    codes = {f.code for f in report.findings}
    assert "TERMINAL_STATUS" in codes
    assert "NO_TAGS" in codes
    assert "NO_PARAMETERS" in codes


def test_format_no_anomalies():
    state = _make_state()
    report = build_anomaly_report(state)
    out = format_anomaly_report(report)
    assert "No anomalies" in out
    assert "my-stack" in out


def test_format_with_anomalies():
    state = _make_state(status="ROLLBACK_COMPLETE", tags={})
    report = build_anomaly_report(state)
    out = format_anomaly_report(report)
    assert "TERMINAL_STATUS" in out
    assert "NO_TAGS" in out
    assert "HIGH" in out
