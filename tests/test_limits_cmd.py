"""Tests for stackwatch.commands.limits_cmd."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.limits_cmd import (
    CfnLimit,
    _fetch_limits,
    _format_limits,
    cmd_limits,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _args(**kwargs):
    defaults = {"region": None, "profile": None, "use_json": False}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_session(limits_raw):
    client = MagicMock()
    client.describe_account_limits.return_value = {"AccountLimits": limits_raw}
    session = MagicMock()
    session.client.return_value = client
    return session


# ---------------------------------------------------------------------------
# CfnLimit unit tests
# ---------------------------------------------------------------------------

def test_remaining_none_when_used_not_set():
    lim = CfnLimit(name="StackCount", value=2000)
    assert lim.remaining is None
    assert lim.pct_used is None


def test_remaining_and_pct():
    lim = CfnLimit(name="StackCount", value=2000, used=400)
    assert lim.remaining == 1600
    assert lim.pct_used == 20.0


# ---------------------------------------------------------------------------
# _fetch_limits
# ---------------------------------------------------------------------------

def test_fetch_limits_maps_fields():
    raw = [{"Name": "StackCount", "Value": 2000}, {"Name": "OutputsPerStack", "Value": 60}]
    session = _make_session(raw)
    limits = _fetch_limits(session)
    assert len(limits) == 2
    assert limits[0].name == "StackCount"
    assert limits[0].value == 2000
    assert limits[1].name == "OutputsPerStack"


def test_fetch_limits_empty():
    session = _make_session([])
    assert _fetch_limits(session) == []


# ---------------------------------------------------------------------------
# _format_limits
# ---------------------------------------------------------------------------

def test_format_limits_plain_contains_name():
    limits = [CfnLimit(name="StackCount", value=2000)]
    out = _format_limits(limits, use_json=False)
    assert "StackCount" in out
    assert "2000" in out


def test_format_limits_json_structure():
    limits = [CfnLimit(name="StackCount", value=2000)]
    out = _format_limits(limits, use_json=True)
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["name"] == "StackCount"
    assert data[0]["limit"] == 2000


# ---------------------------------------------------------------------------
# cmd_limits integration
# ---------------------------------------------------------------------------

def test_returns_0_when_limits_found(capsys):
    raw = [{"Name": "StackCount", "Value": 2000}]
    with patch("stackwatch.commands.limits_cmd.boto3.Session") as MockSession:
        MockSession.return_value = _make_session(raw)
        rc = cmd_limits(_args())
    assert rc == 0
    captured = capsys.readouterr()
    assert "StackCount" in captured.out


def test_returns_0_when_no_limits(capsys):
    with patch("stackwatch.commands.limits_cmd.boto3.Session") as MockSession:
        MockSession.return_value = _make_session([])
        rc = cmd_limits(_args())
    assert rc == 0
    assert "No limit" in capsys.readouterr().out


def test_json_flag_produces_json(capsys):
    raw = [{"Name": "StackCount", "Value": 2000}]
    with patch("stackwatch.commands.limits_cmd.boto3.Session") as MockSession:
        MockSession.return_value = _make_session(raw)
        cmd_limits(_args(use_json=True))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["name"] == "StackCount"
