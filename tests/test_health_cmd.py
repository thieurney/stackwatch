"""Tests for stackwatch.commands.health_cmd."""
import json
import types
import pytest
from unittest.mock import patch, MagicMock

from stackwatch.fetcher import StackState
from stackwatch.commands.health_cmd import cmd_health


def _make_state(
    status="CREATE_COMPLETE",
    extra=None,
) -> StackState:
    return StackState(
        name="my-stack",
        status=status,
        parameters={},
        tags={},
        outputs={},
        extra=extra or {},
    )


def _args(**kwargs):
    defaults = dict(
        stack="my-stack",
        region=None,
        profile=None,
        json_output=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _run(state, **kwargs):
    with patch("stackwatch.commands.health_cmd.fetch_stack", return_value=state):
        return cmd_health(_args(**kwargs))


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.health_cmd.fetch_stack", return_value=None):
        rc = cmd_health(_args())
    assert rc == 1


def test_returns_0_for_healthy_stack():
    rc = _run(_make_state("CREATE_COMPLETE"))
    assert rc == 0


def test_returns_2_for_unhealthy_stack():
    rc = _run(_make_state("UPDATE_FAILED"))
    assert rc == 2


def test_json_output_structure(capsys):
    rc = _run(_make_state("CREATE_COMPLETE"), json_output=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["stack"] == "my-stack"
    assert "score" in data
    assert "grade" in data
    assert "healthy" in data
    assert isinstance(data["issues"], list)


def test_drift_reflected_in_score(capsys):
    state = _make_state(extra={"drift_status": "DRIFTED"})
    rc = _run(state, json_output=True)
    data = json.loads(capsys.readouterr().out)
    assert data["score"] < 100
    assert any("drift" in i["message"].lower() for i in data["issues"])


def test_alarm_count_reflected(capsys):
    state = _make_state(extra={"alarm_count": 2})
    _run(state, json_output=True)
    data = json.loads(capsys.readouterr().out)
    assert data["score"] < 100


def test_plain_output_contains_score(capsys):
    _run(_make_state())
    out = capsys.readouterr().out
    assert "100/100" in out
