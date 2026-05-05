"""Tests for coverage CLI command."""
from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

from stackwatch.commands.coverage_cmd import cmd_coverage
from stackwatch.fetcher import StackState


def _make_state(
    name: str = "my-stack",
    termination: bool = True,
    tags: dict | None = None,
    notifications: list | None = None,
    description: str = "desc",
) -> StackState:
    raw = {
        "StackName": name,
        "StackStatus": "UPDATE_COMPLETE",
        "EnableTerminationProtection": termination,
        "NotificationARNs": notifications or [],
        "Description": description,
    }
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        tags=tags if tags is not None else {"env": "prod"},
        raw=raw,
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(
        stacks=["my-stack"],
        region=None,
        profile=None,
        as_json=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def _run(state, **kwargs):
    with patch("stackwatch.commands.coverage_cmd.boto3") as mock_boto3:
        with patch("stackwatch.commands.coverage_cmd.fetch_stack", return_value=state):
            mock_boto3.Session.return_value = MagicMock()
            return cmd_coverage(_args(**kwargs))


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.coverage_cmd.boto3"):
        with patch("stackwatch.commands.coverage_cmd.fetch_stack", return_value=None):
            rc = cmd_coverage(_args())
    assert rc == 1


def test_returns_0_for_fully_covered_stack():
    state = _make_state(notifications=["arn:aws:sns:us-east-1:123:x"])
    rc = _run(state)
    assert rc == 0


def test_returns_1_when_high_gap_present():
    state = _make_state(termination=False)
    rc = _run(state)
    assert rc == 1


def test_json_output_structure(capsys):
    state = _make_state(notifications=["arn:aws:sns:us-east-1:123:x"])
    _run(state, as_json=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert data[0]["stack"] == "my-stack"
    assert "score" in data[0]
    assert "gaps" in data[0]


def test_plain_output_contains_stack_name(capsys):
    state = _make_state(notifications=["arn:aws:sns:us-east-1:123:x"])
    _run(state)
    captured = capsys.readouterr()
    assert "my-stack" in captured.out


def test_multiple_stacks_all_missing_returns_1():
    with patch("stackwatch.commands.coverage_cmd.boto3"):
        with patch("stackwatch.commands.coverage_cmd.fetch_stack", return_value=None):
            rc = cmd_coverage(_args(stacks=["a", "b"]))
    assert rc == 1
