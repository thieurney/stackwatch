"""Tests for stackwatch.commands.ownership_cmd."""
import argparse
import json
from unittest.mock import MagicMock, patch

from stackwatch.commands.ownership_cmd import cmd_ownership
from stackwatch.fetcher import StackState


def _make_state(tags: dict | None = None) -> StackState:
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags=tags or {},
        outputs=[],
        capabilities=[],
        termination_protection=True,
        creation_time=None,
        last_updated=None,
        description="",
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(stack="my-stack", region=None, profile=None, as_json=False, no_color=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _run(state, **kwargs):
    with patch("stackwatch.commands.ownership_cmd.boto3") as mock_boto3, \
         patch("stackwatch.commands.ownership_cmd.fetch_stack", return_value=state):
        mock_boto3.Session.return_value = MagicMock()
        return cmd_ownership(_args(**kwargs))


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.ownership_cmd.boto3"), \
         patch("stackwatch.commands.ownership_cmd.fetch_stack", return_value=None):
        result = cmd_ownership(_args())
    assert result == 1


def test_returns_0_when_stack_found():
    result = _run(_make_state({"Owner": "alice"}))
    assert result == 0


def test_plain_output_contains_owner(capsys):
    _run(_make_state({"Owner": "alice", "Team": "platform"}))
    out = capsys.readouterr().out
    assert "alice" in out
    assert "platform" in out


def test_json_output_structure(capsys):
    _run(_make_state({"Owner": "carol", "Environment": "prod"}), as_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["owner"] == "carol"
    assert data["environment"] == "prod"
    assert data["is_owned"] is True


def test_json_output_unowned(capsys):
    _run(_make_state(), as_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["owner"] is None
    assert data["is_owned"] is False


def test_plain_output_warns_when_unowned(capsys):
    _run(_make_state())
    out = capsys.readouterr().out
    assert "WARNING" in out
