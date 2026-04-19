"""Tests for the history command."""
from __future__ import annotations

import argparse
from unittest.mock import patch, MagicMock

import pytest

from stackwatch.commands.history_cmd import cmd_history
from stackwatch.fetcher import StackState


def _args(**kwargs):
    defaults = dict(
        stack_name="my-stack",
        snapshot_dir=".stackwatch",
        limit=10,
        diff=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_state(status="CREATE_COMPLETE", params=None):
    return StackState(
        stack_name="my-stack",
        status=status,
        parameters=params or {},
        outputs={},
        tags={},
    )


def test_no_snapshots_prints_no_data(capsys):
    with patch("stackwatch.commands.history_cmd.list_snapshots", return_value=[]):
        rc = cmd_history(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "no data" in out.lower() or "my-stack" in out


def test_lists_snapshots(capsys):
    labels = ["2024-01-01T00:00:00", "2024-01-02T00:00:00"]
    with patch("stackwatch.commands.history_cmd.list_snapshots", return_value=labels):
        rc = cmd_history(_args())
    assert rc == 0
    out = capsys.readouterr().out
    for label in labels:
        assert label in out


def test_limit_is_respected(capsys):
    labels = [f"2024-01-0{i}T00:00:00" for i in range(1, 6)]
    with patch("stackwatch.commands.history_cmd.list_snapshots", return_value=labels):
        rc = cmd_history(_args(limit=2))
    assert rc == 0
    out = capsys.readouterr().out
    assert "2 of 5" in out


def test_diff_flag_shows_changes(capsys):
    labels = ["snap-1", "snap-2"]
    old = make_state(status="CREATE_COMPLETE")
    new = make_state(status="UPDATE_COMPLETE")
    with patch("stackwatch.commands.history_cmd.list_snapshots", return_value=labels), \
         patch("stackwatch.commands.history_cmd.load_snapshot", side_effect=[old, new]):
        rc = cmd_history(_args(diff=True))
    assert rc == 0
    out = capsys.readouterr().out
    assert "snap-1" in out
    assert "snap-2" in out


def test_diff_skips_when_load_returns_none(capsys):
    labels = ["snap-1", "snap-2"]
    with patch("stackwatch.commands.history_cmd.list_snapshots", return_value=labels), \
         patch("stackwatch.commands.history_cmd.load_snapshot", return_value=None):
        rc = cmd_history(_args(diff=True))
    assert rc == 0
