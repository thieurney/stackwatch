"""Tests for scheduler_cmd."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.scheduler_cmd import (
    SchedulerRule,
    _fetch_scheduler_rules,
    _format_rules,
    cmd_scheduler,
)


def _make_session(rules=None, tags=None):
    """Build a mock boto3 session whose events client returns given rules."""
    if rules is None:
        rules = []
    if tags is None:
        tags = {}

    client = MagicMock()

    paginator = MagicMock()
    paginator.paginate.return_value = [{"Rules": rules}]
    client.get_paginator.return_value = paginator

    def _list_tags(ResourceARN):
        stack_name = tags.get(ResourceARN, "other-stack")
        return {"Tags": [{"Key": "aws:cloudformation:stack-name", "Value": stack_name}]}

    client.list_tags_for_resource.side_effect = _list_tags
    client.list_targets_by_rule.return_value = {
        "Targets": [{"Arn": "arn:aws:lambda:us-east-1:123:function:MyFn"}]
    }

    session = MagicMock()
    session.client.return_value = client
    return session


def _args(**kwargs):
    defaults = {"stack": "my-stack", "region": None, "profile": None, "use_json": False}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _format_rules
# ---------------------------------------------------------------------------

def test_format_empty_plain():
    out = _format_rules([], use_json=False)
    assert "no EventBridge rules" in out


def test_format_single_plain():
    rule = SchedulerRule(
        name="my-rule",
        schedule="rate(5 minutes)",
        state="ENABLED",
        description="Fires every 5 min",
        target_arn="arn:aws:lambda:::function:Fn",
    )
    out = _format_rules([rule], use_json=False)
    assert "my-rule" in out
    assert "ENABLED" in out
    assert "rate(5 minutes)" in out
    assert "Fires every 5 min" in out


def test_format_json_output():
    import json
    rule = SchedulerRule(name="r", schedule="cron(0 * * * ? *)", state="DISABLED", description=None, target_arn=None)
    out = _format_rules([rule], use_json=True)
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["name"] == "r"
    assert data[0]["state"] == "DISABLED"


# ---------------------------------------------------------------------------
# _fetch_scheduler_rules
# ---------------------------------------------------------------------------

def test_fetch_returns_empty_when_no_matching_tags():
    raw_rule = {"Name": "unrelated-rule", "Arn": "arn:1", "State": "ENABLED"}
    session = _make_session(rules=[raw_rule], tags={"arn:1": "other-stack"})
    result = _fetch_scheduler_rules(session, "my-stack")
    assert result == []


def test_fetch_returns_rule_for_matching_stack():
    raw_rule = {"Name": "my-rule", "Arn": "arn:2", "State": "ENABLED",
                "ScheduleExpression": "rate(1 hour)", "Description": "hourly"}
    session = _make_session(rules=[raw_rule], tags={"arn:2": "my-stack"})
    result = _fetch_scheduler_rules(session, "my-stack")
    assert len(result) == 1
    assert result[0].name == "my-rule"
    assert result[0].schedule == "rate(1 hour)"
    assert result[0].target_arn == "arn:aws:lambda:us-east-1:123:function:MyFn"


# ---------------------------------------------------------------------------
# cmd_scheduler
# ---------------------------------------------------------------------------

def test_cmd_returns_0(capsys):
    raw_rule = {"Name": "r", "Arn": "arn:3", "State": "ENABLED"}
    session = _make_session(rules=[raw_rule], tags={"arn:3": "my-stack"})
    rc = cmd_scheduler(_args(), session=session)
    assert rc == 0
    captured = capsys.readouterr()
    assert "r" in captured.out
