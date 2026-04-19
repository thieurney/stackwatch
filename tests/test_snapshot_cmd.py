"""Tests for snapshot CLI command handlers."""

import types
from unittest.mock import patch, MagicMock

import pytest

from stackwatch.fetcher import StackState
from stackwatch.commands.snapshot_cmd import (
    cmd_snapshot_save,
    cmd_snapshot_diff,
    cmd_snapshot_list,
)


def _args(**kwargs):
    defaults = {"stack_name": "my-stack", "label": "baseline",
                "region": None, "profile": None, "directory": None, "no_color": True}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def make_state(name="my-stack"):
    return StackState(
        stack_name=name, status="CREATE_COMPLETE",
        parameters={"Env": "prod"}, outputs={}, tags={},
    )


class TestCmdSnapshotSave:
    def test_saves_and_prints_path(self, tmp_path):
        state = make_state()
        with patch("stackwatch.commands.snapshot_cmd.fetch_stack", return_value=state), \
             patch("stackwatch.commands.snapshot_cmd.save_snapshot", return_value="/tmp/snap.json") as mock_save:
            rc = cmd_snapshot_save(_args(directory=str(tmp_path)))
        assert rc == 0
        mock_save.assert_called_once()

    def test_returns_1_when_stack_not_found(self, capsys):
        with patch("stackwatch.commands.snapshot_cmd.fetch_stack", return_value=None):
            rc = cmd_snapshot_save(_args())
        assert rc == 1


class TestCmdSnapshotDiff:
    def test_no_snapshot_returns_1(self, capsys):
        with patch("stackwatch.commands.snapshot_cmd.load_snapshot", return_value=None):
            rc = cmd_snapshot_diff(_args())
        assert rc == 1
        out = capsys.readouterr().out
        assert "No snapshot found" in out

    def test_live_stack_missing_returns_1(self):
        with patch("stackwatch.commands.snapshot_cmd.load_snapshot", return_value=make_state()), \
             patch("stackwatch.commands.snapshot_cmd.fetch_stack", return_value=None):
            rc = cmd_snapshot_diff(_args())
        assert rc == 1

    def test_no_changes_returns_0(self):
        state = make_state()
        with patch("stackwatch.commands.snapshot_cmd.load_snapshot", return_value=state), \
             patch("stackwatch.commands.snapshot_cmd.fetch_stack", return_value=state):
            rc = cmd_snapshot_diff(_args())
        assert rc == 0

    def test_changes_returns_1(self):
        old = make_state()
        new = StackState(stack_name="my-stack", status="UPDATE_COMPLETE",
                         parameters={"Env": "prod"}, outputs={}, tags={})
        with patch("stackwatch.commands.snapshot_cmd.load_snapshot", return_value=old), \
             patch("stackwatch.commands.snapshot_cmd.fetch_stack", return_value=new):
            rc = cmd_snapshot_diff(_args())
        assert rc == 1


class TestCmdSnapshotList:
    def test_empty(self, capsys):
        with patch("stackwatch.commands.snapshot_cmd.list_snapshots", return_value=[]):
            rc = cmd_snapshot_list(_args())
        assert rc == 0
        assert "No snapshots" in capsys.readouterr().out

    def test_lists_entries(self, capsys):
        entries = [{"stack_name": "s", "label": "v1", "status": "OK", "saved_at": "2024-01-01T00:00:00+00:00"}]
        with patch("stackwatch.commands.snapshot_cmd.list_snapshots", return_value=entries):
            rc = cmd_snapshot_list(_args())
        assert rc == 0
        out = capsys.readouterr().out
        assert "v1" in out
        assert "2024-01-01" in out
