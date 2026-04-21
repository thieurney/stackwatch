"""Tests for stackwatch/commands/metadata_cmd.py"""
from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.metadata_cmd import cmd_metadata, _fetch_metadata
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="CREATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )


def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "stack": "my-stack",
        "region": None,
        "profile": None,
        "output_json": False,
        "key": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_returns_1_when_stack_not_found(mock_fetch, mock_meta):
    mock_fetch.return_value = None
    result = cmd_metadata(_args())
    assert result == 1
    mock_meta.assert_not_called()


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_returns_0_when_no_metadata(mock_fetch, mock_meta, capsys):
    mock_fetch.return_value = _make_state()
    mock_meta.return_value = None
    result = cmd_metadata(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "No metadata" in out


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_json_output(mock_fetch, mock_meta, capsys):
    mock_fetch.return_value = _make_state()
    mock_meta.return_value = {"Author": "alice", "Version": "1.0"}
    result = cmd_metadata(_args(output_json=True))
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["Author"] == "alice"
    assert data["Version"] == "1.0"


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_key_filter_found(mock_fetch, mock_meta, capsys):
    mock_fetch.return_value = _make_state()
    mock_meta.return_value = {"Owner": "team-a", "Env": "prod"}
    result = cmd_metadata(_args(key="Owner"))
    assert result == 0
    assert "team-a" in capsys.readouterr().out


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_key_filter_missing(mock_fetch, mock_meta, capsys):
    mock_fetch.return_value = _make_state()
    mock_meta.return_value = {"Owner": "team-a"}
    result = cmd_metadata(_args(key="Missing"))
    assert result == 1
    assert "not found" in capsys.readouterr().out


@patch("stackwatch.commands.metadata_cmd._fetch_metadata")
@patch("stackwatch.commands.metadata_cmd.fetch_stack")
def test_plain_text_output(mock_fetch, mock_meta, capsys):
    mock_fetch.return_value = _make_state()
    mock_meta.return_value = {"CostCenter": "42", "Team": "infra"}
    result = cmd_metadata(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "CostCenter" in out
    assert "42" in out
    assert "Team" in out
