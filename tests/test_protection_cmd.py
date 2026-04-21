"""Tests for protection_cmd and protection module."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.protection_cmd import cmd_protection
from stackwatch.fetcher import StackState
from stackwatch.protection import (
    ProtectionReport,
    build_protection_report,
    format_protection_report,
)


def _make_state(**kwargs) -> StackState:
    defaults = dict(
        name="my-stack",
        status="CREATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        stack="my-stack",
        region="us-east-1",
        profile=None,
        enable=False,
        disable=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- protection module unit tests ---

def test_build_report_no_warnings():
    report = build_protection_report("s", True, "CREATE_COMPLETE")
    assert report.is_protected is True
    assert report.warnings == []


def test_build_report_warns_when_not_protected():
    report = build_protection_report("s", False, "CREATE_COMPLETE")
    assert not report.is_protected
    assert len(report.warnings) == 1
    assert "DISABLED" in report.warnings[0]


def test_build_report_warns_on_delete_status():
    report = build_protection_report("s", True, "DELETE_IN_PROGRESS")
    assert any("deletion" in w for w in report.warnings)


def test_format_protection_no_color():
    report = ProtectionReport(
        stack_name="s", termination_protection=True, stack_status="CREATE_COMPLETE"
    )
    text = format_protection_report(report, color=False)
    assert "enabled" in text
    assert "\033[" not in text


def test_format_protection_shows_warnings():
    report = build_protection_report("s", False, "CREATE_COMPLETE")
    text = format_protection_report(report, color=False)
    assert "Warnings" in text
    assert "DISABLED" in text


# --- cmd_protection integration tests ---

def test_returns_1_when_stack_not_found(capsys):
    with patch("stackwatch.commands.protection_cmd.boto3.Session"), \
         patch("stackwatch.commands.protection_cmd.fetch_stack", return_value=None):
        rc = cmd_protection(_args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_returns_0_and_prints_status(capsys):
    state = _make_state()
    mock_session = MagicMock()
    cf_client = MagicMock()
    mock_session.client.return_value = cf_client
    cf_client.describe_stacks.return_value = {
        "Stacks": [{"EnableTerminationProtection": True, "StackStatus": "CREATE_COMPLETE"}]
    }
    with patch("stackwatch.commands.protection_cmd.boto3.Session", return_value=mock_session), \
         patch("stackwatch.commands.protection_cmd.fetch_stack", return_value=state):
        rc = cmd_protection(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "Termination protection" in out


def test_enable_calls_toggle(capsys):
    state = _make_state()
    mock_session = MagicMock()
    cf_client = MagicMock()
    mock_session.client.return_value = cf_client
    with patch("stackwatch.commands.protection_cmd.boto3.Session", return_value=mock_session), \
         patch("stackwatch.commands.protection_cmd.fetch_stack", return_value=state):
        rc = cmd_protection(_args(enable=True))
    assert rc == 0
    cf_client.update_termination_protection.assert_called_once_with(
        EnableTerminationProtection=True, StackName="my-stack"
    )
    out = capsys.readouterr().out
    assert "enabled" in out
