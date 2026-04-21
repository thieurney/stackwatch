"""Tests for stackwatch.commands.rollback_cmd."""
from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.rollback_cmd import (
    _format_rollback_config,
    cmd_rollback,
)
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs={},
        capabilities=[],
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(stack="my-stack", profile=None, region=None, as_json=False)
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# _format_rollback_config
# ---------------------------------------------------------------------------

def test_format_no_triggers():
    assert _format_rollback_config({}) == "No rollback triggers configured."
    assert _format_rollback_config({"RollbackTriggers": []}) == "No rollback triggers configured."


def test_format_with_triggers():
    config = {
        "MonitoringTimeInMinutes": 5,
        "RollbackTriggers": [
            {"Arn": "arn:aws:cloudwatch:us-east-1:123:alarm:MyAlarm", "Type": "AWS::CloudWatch::Alarm"}
        ],
    }
    result = _format_rollback_config(config)
    assert "5 minute" in result
    assert "MyAlarm" in result
    assert "AWS::CloudWatch::Alarm" in result


# ---------------------------------------------------------------------------
# cmd_rollback
# ---------------------------------------------------------------------------

def _run(args: Namespace, state, rollback_config: dict) -> int:
    with patch("stackwatch.commands.rollback_cmd.boto3.Session") as mock_session_cls, \
         patch("stackwatch.commands.rollback_cmd.fetch_stack", return_value=state), \
         patch("stackwatch.commands.rollback_cmd._fetch_rollback_config", return_value=rollback_config):
        mock_session_cls.return_value = MagicMock()
        return cmd_rollback(args)


def test_returns_1_when_stack_not_found():
    assert _run(_args(), None, {}) == 1


def test_returns_0_with_no_triggers(capsys):
    rc = _run(_args(), _make_state(), {})
    assert rc == 0
    captured = capsys.readouterr()
    assert "No rollback triggers" in captured.out


def test_returns_0_with_triggers(capsys):
    config = {
        "MonitoringTimeInMinutes": 10,
        "RollbackTriggers": [
            {"Arn": "arn:aws:cloudwatch:us-east-1:123:alarm:CpuAlarm", "Type": "AWS::CloudWatch::Alarm"}
        ],
    }
    rc = _run(_args(), _make_state(), config)
    assert rc == 0
    out = capsys.readouterr().out
    assert "CpuAlarm" in out


def test_json_output(capsys):
    import json
    config = {"MonitoringTimeInMinutes": 3, "RollbackTriggers": []}
    rc = _run(_args(as_json=True), _make_state(), config)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["MonitoringTimeInMinutes"] == 3
