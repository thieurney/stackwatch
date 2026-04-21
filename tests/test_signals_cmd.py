"""Tests for signals_cmd."""
from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.signals_cmd import (
    StackSignal,
    _fetch_signals,
    cmd_signals,
)
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="CREATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(
        stack="my-stack",
        resource="MyWaitCondition",
        region=None,
        profile=None,
        as_json=False,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


# ---------------------------------------------------------------------------
# _fetch_signals unit tests
# ---------------------------------------------------------------------------

def test_fetch_signals_returns_empty_on_client_error():
    session = MagicMock()
    cf = session.client.return_value
    cf.exceptions.ClientError = Exception
    cf.describe_stack_resource.side_effect = Exception("not found")

    result = _fetch_signals("my-stack", "MyWC", session)
    assert result == []


def test_fetch_signals_parses_metadata():
    payload = {
        "uid-1": {"Status": "SUCCESS", "Reason": "all good"},
        "uid-2": {"Status": "FAILURE", "Reason": "timed out"},
    }
    session = MagicMock()
    cf = session.client.return_value
    cf.exceptions.ClientError = Exception
    cf.describe_stack_resource.return_value = {
        "StackResourceDetail": {"Metadata": json.dumps(payload)}
    }

    signals = _fetch_signals("my-stack", "MyWC", session)
    assert len(signals) == 2
    statuses = {s.unique_id: s.status for s in signals}
    assert statuses["uid-1"] == "SUCCESS"
    assert statuses["uid-2"] == "FAILURE"


# ---------------------------------------------------------------------------
# cmd_signals integration tests
# ---------------------------------------------------------------------------

def test_returns_1_when_stack_not_found(capsys):
    with patch("stackwatch.commands.signals_cmd.fetch_stack", return_value=None), \
         patch("stackwatch.commands.signals_cmd.boto3.Session"):
        rc = cmd_signals(_args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_returns_0_with_no_signals(capsys):
    with patch("stackwatch.commands.signals_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.signals_cmd.boto3.Session"), \
         patch("stackwatch.commands.signals_cmd._fetch_signals", return_value=[]):
        rc = cmd_signals(_args())
    assert rc == 0
    assert "No signals" in capsys.readouterr().out


def test_returns_0_with_signals_table(capsys):
    signals = [
        StackSignal(
            logical_resource_id="MyWC",
            status="SUCCESS",
            status_reason="OK",
            unique_id="abc-123",
        )
    ]
    with patch("stackwatch.commands.signals_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.signals_cmd.boto3.Session"), \
         patch("stackwatch.commands.signals_cmd._fetch_signals", return_value=signals):
        rc = cmd_signals(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "abc-123" in out
    assert "SUCCESS" in out


def test_json_output(capsys):
    signals = [
        StackSignal(
            logical_resource_id="MyWC",
            status="SUCCESS",
            status_reason="OK",
            unique_id="abc-123",
        )
    ]
    with patch("stackwatch.commands.signals_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.signals_cmd.boto3.Session"), \
         patch("stackwatch.commands.signals_cmd._fetch_signals", return_value=signals):
        rc = cmd_signals(_args(as_json=True))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["unique_id"] == "abc-123"
    assert data[0]["status"] == "SUCCESS"
