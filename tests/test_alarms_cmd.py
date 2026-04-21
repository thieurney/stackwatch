"""Tests for alarms_cmd and alarms module."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.alarms import (
    AlarmSummary,
    StackAlarm,
    parse_alarm,
    format_alarm_summary,
)
from stackwatch.commands.alarms_cmd import _fetch_alarms, cmd_alarms


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_state(name="my-stack"):
    from stackwatch.fetcher import StackState
    return StackState(name=name, status="CREATE_COMPLETE", parameters={}, tags={}, outputs={})


def _args(**kwargs):
    defaults = dict(stack="my-stack", profile=None, region=None, no_color=True, output_json=False)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# unit: parse_alarm
# ---------------------------------------------------------------------------

def test_parse_alarm_basic():
    raw = {
        "AlarmName": "cpu-high",
        "StateValue": "ALARM",
        "MetricName": "CPUUtilization",
        "Namespace": "AWS/EC2",
        "Threshold": 80.0,
        "ComparisonOperator": "GreaterThanThreshold",
    }
    alarm = parse_alarm(raw)
    assert alarm.name == "cpu-high"
    assert alarm.state == "ALARM"
    assert alarm.threshold == 80.0


def test_parse_alarm_falls_back_to_metrics_list():
    raw = {
        "AlarmName": "composite",
        "StateValue": "OK",
        "Metrics": [{"MetricStat": {"Metric": {"MetricName": "Errors", "Namespace": "AWS/Lambda"}}}],
    }
    alarm = parse_alarm(raw)
    assert alarm.metric == "Errors"
    assert alarm.namespace == "AWS/Lambda"


# ---------------------------------------------------------------------------
# unit: format_alarm_summary
# ---------------------------------------------------------------------------

def test_format_no_alarms():
    s = AlarmSummary(alarms=[])
    out = format_alarm_summary(s, color=False)
    assert "No alarms" in out


def test_format_json_output():
    s = AlarmSummary(alarms=[
        StackAlarm(name="a1", state="OK", metric="M", namespace="NS", threshold=5.0, comparison="GT")
    ])
    out = format_alarm_summary(s, color=False, fmt="json")
    data = json.loads(out)
    assert data[0]["name"] == "a1"
    assert data[0]["state"] == "OK"


def test_format_plain_shows_counts():
    s = AlarmSummary(alarms=[
        StackAlarm(name="a1", state="ALARM", metric="M", namespace="NS"),
        StackAlarm(name="a2", state="OK", metric="M", namespace="NS"),
    ])
    out = format_alarm_summary(s, color=False)
    assert "1 ALARM" in out
    assert "1 OK" in out


# ---------------------------------------------------------------------------
# integration: cmd_alarms
# ---------------------------------------------------------------------------

def _make_session(alarm_names=None, alarm_details=None):
    alarm_names = alarm_names or []
    alarm_details = alarm_details or []

    resource_summaries = [
        {"ResourceType": "AWS::CloudWatch::Alarm", "PhysicalResourceId": n}
        for n in alarm_names
    ]

    paginator = MagicMock()
    paginator.paginate.return_value = [{"StackResourceSummaries": resource_summaries}]

    cfn = MagicMock()
    cfn.get_paginator.return_value = paginator

    cw = MagicMock()
    cw.describe_alarms.return_value = {"MetricAlarms": alarm_details, "CompositeAlarms": []}

    session = MagicMock()
    session.client.side_effect = lambda svc, **kw: cfn if svc == "cloudformation" else cw
    return session


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.alarms_cmd.fetch_stack", return_value=None), \
         patch("stackwatch.commands.alarms_cmd.boto3.Session"):
        rc = cmd_alarms(_args())
    assert rc == 1


def test_returns_0_with_no_alarms(capsys):
    session = _make_session()
    with patch("stackwatch.commands.alarms_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.alarms_cmd.boto3.Session", return_value=session):
        rc = cmd_alarms(_args())
    assert rc == 0
    captured = capsys.readouterr()
    assert "No alarms" in captured.out


def test_returns_0_with_alarms(capsys):
    raw = {"AlarmName": "cpu", "StateValue": "OK", "MetricName": "CPU", "Namespace": "AWS/EC2"}
    session = _make_session(alarm_names=["cpu"], alarm_details=[raw])
    with patch("stackwatch.commands.alarms_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.alarms_cmd.boto3.Session", return_value=session):
        rc = cmd_alarms(_args())
    assert rc == 0
    captured = capsys.readouterr()
    assert "cpu" in captured.out
