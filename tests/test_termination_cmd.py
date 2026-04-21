"""Tests for stackwatch/commands/termination_cmd.py"""
from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.termination_cmd import (
    _fetch_termination_status,
    _toggle_termination,
    cmd_termination,
)
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "stack": "my-stack",
        "region": None,
        "profile": None,
        "action": None,
        "as_json": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@patch("stackwatch.commands.termination_cmd.fetch_stack", return_value=None)
def test_returns_1_when_stack_not_found(mock_fetch, capsys):
    session = MagicMock()
    rc = cmd_termination(_args(), session)
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


@patch("stackwatch.commands.termination_cmd._fetch_termination_status", return_value=True)
@patch("stackwatch.commands.termination_cmd.fetch_stack")
def test_shows_enabled_status(mock_fetch, mock_status, capsys):
    mock_fetch.return_value = _make_state()
    session = MagicMock()
    rc = cmd_termination(_args(), session)
    assert rc == 0
    out = capsys.readouterr().out
    assert "enabled" in out


@patch("stackwatch.commands.termination_cmd._fetch_termination_status", return_value=False)
@patch("stackwatch.commands.termination_cmd.fetch_stack")
def test_shows_disabled_status(mock_fetch, mock_status, capsys):
    mock_fetch.return_value = _make_state()
    session = MagicMock()
    rc = cmd_termination(_args(), session)
    assert rc == 0
    out = capsys.readouterr().out
    assert "disabled" in out


@patch("stackwatch.commands.termination_cmd._fetch_termination_status", return_value=True)
@patch("stackwatch.commands.termination_cmd.fetch_stack")
def test_json_output_read(mock_fetch, mock_status, capsys):
    mock_fetch.return_value = _make_state()
    session = MagicMock()
    rc = cmd_termination(_args(as_json=True), session)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["termination_protection"] is True
    assert data["stack"] == "my-stack"


@patch("stackwatch.commands.termination_cmd._toggle_termination")
@patch("stackwatch.commands.termination_cmd.fetch_stack")
def test_enable_action_calls_toggle(mock_fetch, mock_toggle, capsys):
    mock_fetch.return_value = _make_state()
    session = MagicMock()
    rc = cmd_termination(_args(action="enable"), session)
    assert rc == 0
    mock_toggle.assert_called_once_with(session, "my-stack", True)
    assert "enabled" in capsys.readouterr().out


@patch("stackwatch.commands.termination_cmd._toggle_termination")
@patch("stackwatch.commands.termination_cmd.fetch_stack")
def test_disable_action_json(mock_fetch, mock_toggle, capsys):
    mock_fetch.return_value = _make_state()
    session = MagicMock()
    rc = cmd_termination(_args(action="disable", as_json=True), session)
    assert rc == 0
    mock_toggle.assert_called_once_with(session, "my-stack", False)
    data = json.loads(capsys.readouterr().out)
    assert data["termination_protection"] is False


def test_fetch_termination_status_returns_flag():
    session = MagicMock()
    cf = session.client.return_value
    cf.describe_stacks.return_value = {
        "Stacks": [{"EnableTerminationProtection": True}]
    }
    result = _fetch_termination_status(session, "my-stack")
    assert result is True


def test_fetch_termination_status_empty_stacks():
    session = MagicMock()
    cf = session.client.return_value
    cf.describe_stacks.return_value = {"Stacks": []}
    result = _fetch_termination_status(session, "my-stack")
    assert result is None
