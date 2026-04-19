"""Tests for export_cmd."""
from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.export_cmd import cmd_export
from stackwatch.differ import FieldDiff, StackDiff
from stackwatch.fetcher import StackState


def make_state(name="my-stack", status="UPDATE_COMPLETE", params=None, outputs=None):
    return StackState(
        name=name,
        status=status,
        parameters=params or {},
        outputs=outputs or {},
    )


def _args(**kwargs):
    defaults = dict(
        stack="my-stack",
        env_a="prod",
        env_b=None,
        snapshot="baseline",
        fmt="json",
        output="-",
        dir=".stackwatch",
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


class TestCmdExport:
    @patch("stackwatch.commands.export_cmd.fetch_stack")
    @patch("stackwatch.commands.export_cmd.load_snapshot")
    def test_returns_0_on_success(self, mock_load, mock_fetch, capsys):
        mock_load.return_value = make_state()
        mock_fetch.return_value = make_state(status="UPDATE_IN_PROGRESS")
        rc = cmd_export(_args())
        assert rc == 0

    @patch("stackwatch.commands.export_cmd.fetch_stack")
    @patch("stackwatch.commands.export_cmd.load_snapshot")
    def test_json_output_structure(self, mock_load, mock_fetch, capsys):
        mock_load.return_value = make_state()
        mock_fetch.return_value = make_state(status="UPDATE_IN_PROGRESS")
        cmd_export(_args(fmt="json"))
        captured = capsys.readouterr().out
        data = json.loads(captured)
        assert data["stack"] == "my-stack"
        assert isinstance(data["changes"], list)

    @patch("stackwatch.commands.export_cmd.fetch_stack")
    @patch("stackwatch.commands.export_cmd.load_snapshot")
    def test_returns_1_when_snapshot_missing(self, mock_load, mock_fetch, capsys):
        mock_load.return_value = None
        mock_fetch.return_value = make_state()
        rc = cmd_export(_args())
        assert rc == 1

    @patch("stackwatch.commands.export_cmd.fetch_stack")
    def test_two_env_compare(self, mock_fetch, capsys):
        mock_fetch.side_effect = [make_state(), make_state(status="ROLLBACK_COMPLETE")]
        rc = cmd_export(_args(env_b="staging"))
        assert rc == 0
        captured = capsys.readouterr().out
        data = json.loads(captured)
        assert data["stack"] == "my-stack"

    @patch("stackwatch.commands.export_cmd.fetch_stack")
    @patch("stackwatch.commands.export_cmd.load_snapshot")
    def test_csv_output_has_header(self, mock_load, mock_fetch, capsys):
        mock_load.return_value = make_state(params={"Env": "prod"})
        mock_fetch.return_value = make_state(params={"Env": "staging"})
        cmd_export(_args(fmt="csv"))
        captured = capsys.readouterr().out
        assert "field,old,new" in captured
