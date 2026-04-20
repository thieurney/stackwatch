"""Tests for stackwatch.commands.outputs_cmd."""
from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.outputs_cmd import cmd_outputs
from stackwatch.fetcher import StackState


def _make_state(outputs=None):
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        raw={"Outputs": outputs or []},
    )


def _args(**kwargs):
    defaults = dict(
        stack="my-stack",
        profile=None,
        region=None,
        diff_snapshot=None,
        snapshot_dir=".stackwatch",
        as_json=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_returns_1_when_stack_not_found(capsys):
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=None):
        rc = cmd_outputs(_args())
    assert rc == 1


def test_shows_no_outputs_message(capsys):
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=_make_state()):
        rc = cmd_outputs(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "no outputs" in out.lower()


def test_shows_outputs(capsys):
    state = _make_state([{"OutputKey": "BucketName", "OutputValue": "my-bucket",
                          "Description": "The bucket"}])
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=state):
        rc = cmd_outputs(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "BucketName" in out
    assert "my-bucket" in out
    assert "The bucket" in out


def test_json_output(capsys):
    state = _make_state([{"OutputKey": "Url", "OutputValue": "https://x.com"}])
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=state):
        rc = cmd_outputs(_args(as_json=True))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["key"] == "Url"
    assert data[0]["value"] == "https://x.com"


def test_diff_snapshot_not_found(capsys):
    state = _make_state()
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=state), \
         patch("stackwatch.commands.outputs_cmd.load_snapshot", return_value=None):
        rc = cmd_outputs(_args(diff_snapshot="v1"))
    assert rc == 1
    assert "not found" in capsys.readouterr().out


def test_diff_snapshot_no_changes(capsys):
    state = _make_state([{"OutputKey": "K", "OutputValue": "v"}])
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=state), \
         patch("stackwatch.commands.outputs_cmd.load_snapshot", return_value=state):
        rc = cmd_outputs(_args(diff_snapshot="v1"))
    assert rc == 0
    assert "No output changes" in capsys.readouterr().out


def test_diff_snapshot_with_changes(capsys):
    old = _make_state([{"OutputKey": "Url", "OutputValue": "http://old"}])
    new = _make_state([{"OutputKey": "Url", "OutputValue": "http://new"}])
    with patch("stackwatch.commands.outputs_cmd.fetch_stack", return_value=new), \
         patch("stackwatch.commands.outputs_cmd.load_snapshot", return_value=old):
        rc = cmd_outputs(_args(diff_snapshot="v1"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Url" in out
    assert "http://old" in out
    assert "http://new" in out
