"""Tests for stackwatch.compliance."""
import json
import pytest

from stackwatch.fetcher import StackState
from stackwatch.compliance import (
    build_compliance_report,
    format_compliance_report,
    ComplianceReport,
)


def _make_state(
    name="my-stack",
    status="CREATE_COMPLETE",
    termination_protection=True,
    tags=None,
    description="A test stack",
) -> StackState:
    raw = {
        "StackName": name,
        "StackStatus": status,
        "EnableTerminationProtection": termination_protection,
        "Tags": tags if tags is not None else [{"Key": "env", "Value": "prod"}],
        "Description": description,
    }
    return StackState(name=name, status=status, parameters={}, outputs={}, tags={}, raw=raw)


def test_fully_compliant_stack():
    state = _make_state()
    report = build_compliance_report(state)
    assert report.compliant is True
    assert report.failed == 0
    assert report.passed == 4


def test_termination_protection_disabled():
    state = _make_state(termination_protection=False)
    report = build_compliance_report(state)
    rule = next(r for r in report.rules if r.name == "termination-protection")
    assert rule.passed is False
    assert rule.detail is not None


def test_terminal_failure_status():
    state = _make_state(status="ROLLBACK_FAILED")
    report = build_compliance_report(state)
    rule = next(r for r in report.rules if r.name == "no-terminal-failure")
    assert rule.passed is False
    assert "ROLLBACK_FAILED" in rule.detail


def test_no_tags_fails_rule():
    state = _make_state(tags=[])
    report = build_compliance_report(state)
    rule = next(r for r in report.rules if r.name == "has-tags")
    assert rule.passed is False


def test_no_description_fails_rule():
    state = _make_state(description="")
    report = build_compliance_report(state)
    rule = next(r for r in report.rules if r.name == "has-description")
    assert rule.passed is False


def test_format_plain_no_color():
    state = _make_state()
    report = build_compliance_report(state)
    output = format_compliance_report(report, color=False)
    assert "my-stack" in output
    assert "4/4" in output
    assert "\u2713" in output


def test_format_plain_with_failure():
    state = _make_state(termination_protection=False, tags=[])
    report = build_compliance_report(state)
    output = format_compliance_report(report, color=False)
    assert "\u2717" in output
    assert "2/4" in output


def test_format_json_output():
    state = _make_state(termination_protection=False)
    report = build_compliance_report(state)
    output = format_compliance_report(report, json_output=True)
    data = json.loads(output)
    assert data["stack"] == "my-stack"
    assert data["compliant"] is False
    assert data["failed"] == 1
    assert len(data["rules"]) == 4


def test_report_stack_name():
    state = _make_state(name="prod-stack")
    report = build_compliance_report(state)
    assert report.stack_name == "prod-stack"
