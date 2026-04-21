from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.params_cmd import (
    _build_param_diff,
    _filter_params,
    _params_as_dict,
    cmd_params,
)
from stackwatch.fetcher import StackState


def _make_state(params: list[dict]) -> StackState:
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters=params,
        outputs=[],
        tags={},
        capabilities=[],
        role_arn=None,
        description=None,
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(
        stack="my-stack",
        env="prod",
        compare_env=None,
        key_filter=None,
        as_json=False,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


# --- unit helpers ---

def test_params_as_dict():
    state = _make_state([{"ParameterKey": "Env", "ParameterValue": "prod"}])
    assert _params_as_dict(state) == {"Env": "prod"}


def test_filter_params_none_returns_all():
    params = {"Env": "prod", "Region": "us-east-1"}
    assert _filter_params(params, None) == params


def test_filter_params_by_substring():
    params = {"Env": "prod", "Region": "us-east-1", "DbEnv": "prod"}
    result = _filter_params(params, "env")
    assert result == {"Env": "prod", "DbEnv": "prod"}


def test_build_param_diff_no_change():
    assert _build_param_diff({"A": "1"}, {"A": "1"}) == {}


def test_build_param_diff_changed():
    diff = _build_param_diff({"A": "1"}, {"A": "2"})
    assert diff == {"A": {"old": "1", "new": "2"}}


def test_build_param_diff_missing_in_right():
    diff = _build_param_diff({"A": "1"}, {})
    assert diff == {"A": {"old": "1"}}


def test_build_param_diff_missing_in_left():
    diff = _build_param_diff({}, {"B": "2"})
    assert diff == {"B": {"new": "2"}}


# --- cmd_params integration ---

def test_returns_1_when_stack_not_found(capsys):
    session = MagicMock()
    with patch("stackwatch.commands.params_cmd.fetch_stack", return_value=None):
        rc = cmd_params(_args(), session)
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_returns_0_with_no_params(capsys):
    state = _make_state([])
    session = MagicMock()
    with patch("stackwatch.commands.params_cmd.fetch_stack", return_value=state):
        rc = cmd_params(_args(), session)
    assert rc == 0
    assert "No parameters" in capsys.readouterr().out


def test_shows_params(capsys):
    state = _make_state([{"ParameterKey": "Env", "ParameterValue": "prod"}])
    session = MagicMock()
    with patch("stackwatch.commands.params_cmd.fetch_stack", return_value=state):
        rc = cmd_params(_args(), session)
    assert rc == 0
    assert "Env" in capsys.readouterr().out


def test_diff_returns_0_when_identical(capsys):
    state = _make_state([{"ParameterKey": "Env", "ParameterValue": "prod"}])
    session = MagicMock()
    with patch(
        "stackwatch.commands.params_cmd.fetch_stack", return_value=state
    ):
        rc = cmd_params(_args(compare_env="staging"), session)
    assert rc == 0
    assert "identical" in capsys.readouterr().out


def test_diff_shows_changes(capsys):
    prod_state = _make_state([{"ParameterKey": "Env", "ParameterValue": "prod"}])
    staging_state = _make_state([{"ParameterKey": "Env", "ParameterValue": "staging"}])
    session = MagicMock()
    with patch(
        "stackwatch.commands.params_cmd.fetch_stack",
        side_effect=[prod_state, staging_state],
    ):
        rc = cmd_params(_args(compare_env="staging"), session)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Env" in out
    assert "prod" in out
    assert "staging" in out
