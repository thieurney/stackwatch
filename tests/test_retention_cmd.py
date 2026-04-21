"""Tests for stackwatch.commands.retention_cmd."""
from __future__ import annotations

import argparse
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.retention_cmd import (
    RetentionConfig,
    _fetch_retention,
    _format_retention,
    cmd_retention,
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
        "profile": None,
        "region": None,
        "as_json": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- _format_retention ---

def test_format_no_log_group():
    cfg = RetentionConfig(log_group_name=None, retention_in_days=None)
    result = _format_retention(cfg)
    assert "No log group" in result


def test_format_with_retention():
    cfg = RetentionConfig(log_group_name="/aws/cfn/my-stack", retention_in_days=90)
    result = _format_retention(cfg)
    assert "/aws/cfn/my-stack" in result
    assert "90 days" in result


def test_format_never_expire():
    cfg = RetentionConfig(log_group_name="/aws/cfn/my-stack", retention_in_days=None)
    result = _format_retention(cfg)
    assert "Never expire" in result


# --- cmd_retention ---

def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.retention_cmd.boto3.Session"), \
         patch("stackwatch.commands.retention_cmd.fetch_stack", return_value=None):
        rc = cmd_retention(_args())
    assert rc == 1


def test_returns_0_on_success(capsys):
    cfg = RetentionConfig(log_group_name="/aws/cfn/my-stack", retention_in_days=30)
    with patch("stackwatch.commands.retention_cmd.boto3.Session"), \
         patch("stackwatch.commands.retention_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.retention_cmd._fetch_retention", return_value=cfg):
        rc = cmd_retention(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "30 days" in out


def test_json_output_structure(capsys):
    import json
    cfg = RetentionConfig(log_group_name="/aws/cfn/my-stack", retention_in_days=14)
    with patch("stackwatch.commands.retention_cmd.boto3.Session"), \
         patch("stackwatch.commands.retention_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.retention_cmd._fetch_retention", return_value=cfg):
        rc = cmd_retention(_args(as_json=True))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["stack"] == "my-stack"
    assert data["retention_in_days"] == 14
    assert data["log_group_name"] == "/aws/cfn/my-stack"
