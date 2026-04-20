"""Tests for stackwatch/commands/policy_cmd.py"""
from __future__ import annotations

import json
import argparse
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.policy_cmd import (
    _format_policy,
    cmd_policy,
)
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs={},
        region="us-east-1",
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(stack="my-stack", region=None, profile=None, as_json=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


SAMPLE_POLICY = {
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": "*",
            "Action": "Update:Delete",
            "Resource": "LogicalResourceId/CriticalBucket",
        },
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "Update:*",
            "Resource": "*",
        },
    ]
}


@patch("stackwatch.commands.policy_cmd._fetch_policy")
@patch("stackwatch.commands.policy_cmd.fetch_stack")
def test_returns_1_when_stack_not_found(mock_fetch, mock_policy, capsys):
    mock_fetch.return_value = None
    result = cmd_policy(_args())
    assert result == 1
    mock_policy.assert_not_called()
    out = capsys.readouterr().out
    assert "not found" in out


@patch("stackwatch.commands.policy_cmd._fetch_policy")
@patch("stackwatch.commands.policy_cmd.fetch_stack")
def test_returns_0_when_no_policy(mock_fetch, mock_policy, capsys):
    mock_fetch.return_value = _make_state()
    mock_policy.return_value = None
    result = cmd_policy(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "No stack policy" in out


@patch("stackwatch.commands.policy_cmd._fetch_policy")
@patch("stackwatch.commands.policy_cmd.fetch_stack")
def test_returns_0_and_prints_formatted(mock_fetch, mock_policy, capsys):
    mock_fetch.return_value = _make_state()
    mock_policy.return_value = SAMPLE_POLICY
    result = cmd_policy(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "Deny" in out
    assert "Allow" in out
    assert "CriticalBucket" in out


@patch("stackwatch.commands.policy_cmd._fetch_policy")
@patch("stackwatch.commands.policy_cmd.fetch_stack")
def test_json_flag_outputs_raw_json(mock_fetch, mock_policy, capsys):
    mock_fetch.return_value = _make_state()
    mock_policy.return_value = SAMPLE_POLICY
    result = cmd_policy(_args(as_json=True))
    assert result == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == SAMPLE_POLICY


def test_format_policy_empty_statements():
    result = _format_policy({"Statement": []})
    assert "no statements" in result


def test_format_policy_with_condition():
    policy = {
        "Statement": [
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "Update:Replace",
                "Resource": "*",
                "Condition": {"StringEquals": {"ResourceType": "AWS::RDS::DBInstance"}},
            }
        ]
    }
    result = _format_policy(policy)
    assert "Condition" in result
    assert "RDS" in result
