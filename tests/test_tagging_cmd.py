"""Tests for stackwatch.commands.tagging_cmd."""
import argparse
from unittest.mock import MagicMock, patch

import pytest
from stackwatch.fetcher import StackState
from stackwatch.commands.tagging_cmd import cmd_tagging


def _make_state(tags=None, stack_name="demo-stack"):
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


def _args(**kwargs):
    defaults = dict(
        stack_name="demo-stack",
        region=None,
        profile=None,
        required_tags=None,
        fmt="plain",
        no_color=True,
        fail_on_noncompliant=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _run(state, **kwargs):
    args = _args(**kwargs)
    with patch("stackwatch.commands.tagging_cmd.boto3") as mock_boto:
        mock_boto.Session.return_value = MagicMock()
        with patch("stackwatch.commands.tagging_cmd.fetch_stack", return_value=state):
            return cmd_tagging(args)


def test_returns_1_when_stack_not_found(capsys):
    result = _run(None)
    assert result == 1


def test_returns_0_for_compliant_stack(capsys):
    state = _make_state(tags={"Environment": "prod", "Owner": "alice", "Project": "core"})
    result = _run(state)
    assert result == 0
    out = capsys.readouterr().out
    assert "No issues found." in out


def test_returns_0_for_noncompliant_without_flag(capsys):
    state = _make_state(tags={})
    result = _run(state)
    assert result == 0


def test_returns_2_for_noncompliant_with_flag(capsys):
    state = _make_state(tags={})
    result = _run(state, fail_on_noncompliant=True)
    assert result == 2


def test_json_output_is_valid_json(capsys):
    import json
    state = _make_state(tags={"Environment": "staging", "Owner": "bob", "Project": "y"})
    result = _run(state, fmt="json")
    assert result == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "compliant" in data
    assert data["stack"] == "demo-stack"


def test_custom_required_tags_respected(capsys):
    state = _make_state(tags={"Team": "ops"})
    result = _run(state, required_tags=["Team"])
    assert result == 0
    out = capsys.readouterr().out
    assert "No issues found." in out
