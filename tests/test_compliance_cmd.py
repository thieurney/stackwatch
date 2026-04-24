"""Tests for stackwatch.commands.compliance_cmd."""
import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.fetcher import StackState
from stackwatch.commands.compliance_cmd import cmd_compliance


def _make_state(
    name="my-stack",
    status="CREATE_COMPLETE",
    termination_protection=True,
    tags=None,
    description="A stack",
) -> StackState:
    raw = {
        "StackName": name,
        "StackStatus": status,
        "EnableTerminationProtection": termination_protection,
        "Tags": tags if tags is not None else [{"Key": "env", "Value": "prod"}],
        "Description": description,
    }
    return StackState(name=name, status=status, parameters={}, outputs={}, tags={}, raw=raw)


def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "stack": "my-stack",
        "region": None,
        "profile": None,
        "no_color": True,
        "json_output": False,
        "fail_on_violation": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _run(state, **kwargs):
    args = _args(**kwargs)
    with patch("stackwatch.commands.compliance_cmd.boto3.Session"), \
         patch("stackwatch.commands.compliance_cmd.fetch_stack", return_value=state):
        return cmd_compliance(args)


def test_returns_1_when_stack_not_found(capsys):
    result = _run(None)
    assert result == 1
    out = capsys.readouterr().out
    assert "my-stack" in out


def test_returns_0_for_compliant_stack(capsys):
    state = _make_state()
    result = _run(state)
    assert result == 0


def test_returns_0_for_non_compliant_without_flag(capsys):
    state = _make_state(termination_protection=False)
    result = _run(state)
    assert result == 0


def test_returns_2_with_fail_on_violation(capsys):
    state = _make_state(termination_protection=False)
    result = _run(state, fail_on_violation=True)
    assert result == 2


def test_json_output_is_valid(capsys):
    state = _make_state()
    result = _run(state, json_output=True)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["stack"] == "my-stack"
    assert data["compliant"] is True
    assert result == 0


def test_plain_output_contains_stack_name(capsys):
    state = _make_state()
    _run(state)
    out = capsys.readouterr().out
    assert "my-stack" in out
    assert "4/4" in out
