"""Tests for stackwatch.tagging module."""
import pytest
from stackwatch.fetcher import StackState
from stackwatch.tagging import (
    TaggingReport,
    build_tagging_report,
    compliant,
    format_tagging_report,
    missing_required,
)


def _make_state(tags=None, stack_name="my-stack"):
    return StackState(
        stack_name=stack_name,
        status="CREATE_COMPLETE",
        parameters={},
        outputs={},
        tags=tags or {},
        capabilities=[],
        termination_protection=True,
        creation_time=None,
        last_updated_time=None,
        description=None,
        role_arn=None,
        notification_arns=[],
    )


def test_compliant_with_all_required_tags():
    state = _make_state(tags={"Environment": "prod", "Owner": "alice", "Project": "core"})
    report = build_tagging_report(state)
    assert compliant(report)
    assert report.issues == []


def test_missing_required_tag_creates_high_issue():
    state = _make_state(tags={"Owner": "alice", "Project": "core"})
    report = build_tagging_report(state)
    assert not compliant(report)
    keys = missing_required(report)
    assert "Environment" in keys


def test_no_tags_creates_high_issue():
    state = _make_state(tags={})
    report = build_tagging_report(state)
    assert not compliant(report)
    assert any(i.severity == "high" for i in report.issues)


def test_empty_value_creates_medium_issue():
    state = _make_state(tags={"Environment": "prod", "Owner": "", "Project": "core"})
    report = build_tagging_report(state)
    medium = [i for i in report.issues if i.severity == "medium"]
    assert len(medium) == 1
    assert medium[0].key == "Owner"


def test_custom_required_keys():
    state = _make_state(tags={"Team": "platform"})
    report = build_tagging_report(state, required_keys=["Team"])
    assert compliant(report)


def test_format_plain_no_issues():
    state = _make_state(tags={"Environment": "prod", "Owner": "alice", "Project": "core"})
    report = build_tagging_report(state)
    output = format_tagging_report(report)
    assert "No issues found." in output
    assert "Environment" in output


def test_format_plain_with_issues():
    state = _make_state(tags={})
    report = build_tagging_report(state)
    output = format_tagging_report(report)
    assert "[HIGH]" in output


def test_format_json():
    import json
    state = _make_state(tags={"Environment": "dev", "Owner": "bob", "Project": "x"})
    report = build_tagging_report(state)
    output = format_tagging_report(report, fmt="json")
    data = json.loads(output)
    assert data["compliant"] is True
    assert data["stack"] == "my-stack"
    assert "Environment" in data["tags"]


def test_missing_required_returns_empty_when_all_present():
    state = _make_state(tags={"Environment": "prod", "Owner": "alice", "Project": "core"})
    report = build_tagging_report(state)
    assert missing_required(report) == []
