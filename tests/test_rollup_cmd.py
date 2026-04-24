"""Tests for stackwatch.commands.rollup_cmd."""
import argparse
import pytest
from unittest.mock import MagicMock, patch

from stackwatch.fetcher import StackState
from stackwatch.commands.rollup_cmd import cmd_rollup


def _make_state(name="MyStack", status="CREATE_COMPLETE", region="us-east-1"):
    return StackState(
        name=name,
        status=status,
        region=region,
        parameters={},
        tags={},
        raw={},
    )


def _args(**kwargs):
    defaults = dict(
        stacks=["StackA"],
        region="us-east-1",
        profile=None,
        json_output=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _run(args, side_effects):
    with patch("stackwatch.commands.rollup_cmd.boto3.Session"):
        with patch("stackwatch.commands.rollup_cmd.fetch_stack", side_effect=side_effects) as mock_fetch:
            result = cmd_rollup(args)
    return result, mock_fetch


def test_returns_1_when_all_stacks_missing(capsys):
    result, _ = _run(_args(stacks=["Missing"]), side_effects=[None])
    assert result == 1
    out = capsys.readouterr().out
    assert "No stacks found" in out


def test_warns_about_missing_stack(capsys):
    args = _args(stacks=["Good", "Bad"])
    result, _ = _run(args, side_effects=[_make_state("Good"), None])
    out = capsys.readouterr().out
    assert "Bad" in out
    assert result == 0


def test_returns_0_on_success(capsys):
    result, _ = _run(_args(stacks=["StackA"]), side_effects=[_make_state("StackA")])
    assert result == 0


def test_plain_output_contains_stack_name(capsys):
    _run(_args(stacks=["StackA"]), side_effects=[_make_state("StackA")])
    out = capsys.readouterr().out
    assert "StackA" in out


def test_json_output_is_valid_json(capsys):
    import json
    args = _args(stacks=["StackA"], json_output=True)
    _run(args, side_effects=[_make_state("StackA")])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["total"] == 1


def test_multiple_stacks_aggregated(capsys):
    import json
    args = _args(stacks=["A", "B", "C"], json_output=True)
    states = [_make_state("A"), _make_state("B", "ROLLBACK_COMPLETE"), _make_state("C")]
    _run(args, side_effects=states)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["total"] == 3
    assert data["failed"] == 1
    assert data["healthy"] == 2
