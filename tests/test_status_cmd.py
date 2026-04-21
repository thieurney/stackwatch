"""Tests for stackwatch/commands/status_cmd.py"""
from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.status_cmd import (
    StatusRow,
    _build_row,
    _colorize,
    _format_table,
    cmd_status,
)
from stackwatch.fetcher import StackState


def _make_state(name="my-stack", status="CREATE_COMPLETE", drift="IN_SYNC", prot=True):
    raw = {
        "DriftInformation": {"StackDriftStatus": drift},
        "EnableTerminationProtection": prot,
    }
    return StackState(stack_name=name, status=status, parameters={}, tags={}, raw=raw)


def _args(**kwargs):
    defaults = {
        "stacks": ["my-stack"],
        "region": "eu-west-1",
        "profile": None,
        "as_json": False,
        "no_color": True,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_colorize_no_color():
    assert _colorize("CREATE_COMPLETE", False) == "CREATE_COMPLETE"


def test_colorize_known_status_adds_escape():
    result = _colorize("CREATE_COMPLETE", True)
    assert "CREATE_COMPLETE" in result
    assert "\033[" in result


def test_colorize_unknown_status_unchanged():
    assert _colorize("WEIRD_STATUS", True) == "WEIRD_STATUS"


def test_build_row_maps_fields():
    state = _make_state(drift="DRIFTED", prot=False)
    row = _build_row(state, "ap-southeast-1")
    assert row.stack_name == "my-stack"
    assert row.status == "CREATE_COMPLETE"
    assert row.region == "ap-southeast-1"
    assert row.drift == "DRIFTED"
    assert row.termination_protection is False


def test_build_row_no_drift_info():
    state = StackState(stack_name="s", status="UPDATE_COMPLETE", parameters={}, tags={}, raw={})
    row = _build_row(state, "us-east-1")
    assert row.drift is None
    assert row.termination_protection is False


def test_format_table_contains_stack_name():
    rows = [StatusRow("my-stack", "CREATE_COMPLETE", "eu-west-1", "IN_SYNC", True)]
    table = _format_table(rows, use_color=False)
    assert "my-stack" in table
    assert "CREATE_COMPLETE" in table
    assert "IN_SYNC" in table
    assert "yes" in table


# ---------------------------------------------------------------------------
# Integration-style tests for cmd_status
# ---------------------------------------------------------------------------

def test_returns_1_when_no_stacks_found(capsys):
    with patch("stackwatch.commands.status_cmd.boto3.Session") as mock_sess, \
         patch("stackwatch.commands.status_cmd.fetch_stack", return_value=None):
        mock_sess.return_value.region_name = "us-east-1"
        rc = cmd_status(_args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_returns_0_with_found_stack(capsys):
    state = _make_state()
    with patch("stackwatch.commands.status_cmd.boto3.Session") as mock_sess, \
         patch("stackwatch.commands.status_cmd.fetch_stack", return_value=state):
        mock_sess.return_value.region_name = "eu-west-1"
        rc = cmd_status(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "my-stack" in out


def test_json_output_structure(capsys):
    state = _make_state()
    with patch("stackwatch.commands.status_cmd.boto3.Session") as mock_sess, \
         patch("stackwatch.commands.status_cmd.fetch_stack", return_value=state):
        mock_sess.return_value.region_name = "eu-west-1"
        rc = cmd_status(_args(as_json=True))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["stack_name"] == "my-stack"
    assert "status" in data[0]
    assert "drift" in data[0]
