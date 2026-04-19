"""Tests for the compare command."""
from __future__ import annotations

import argparse
from unittest.mock import patch, MagicMock

import pytest

from stackwatch.fetcher import StackState
from stackwatch.commands.compare_cmd import cmd_compare


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        stack_name="my-stack",
        env_a="dev",
        env_b="prod",
        region_a=None,
        region_b=None,
        no_color=True,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_state(status="CREATE_COMPLETE", params=None, outputs=None) -> StackState:
    return StackState(
        name="my-stack",
        status=status,
        parameters=params or {},
        outputs=outputs or {},
    )


class TestCmdCompare:
    def _run(self, state_a, state_b, **kw):
        with patch("stackwatch.commands.compare_cmd.fetch_stack", side_effect=[state_a, state_b]):
            return cmd_compare(_args(**kw))

    def test_returns_0_when_no_changes(self):
        s = make_state()
        assert self._run(s, s) == 0

    def test_returns_2_when_changes(self):
        a = make_state(status="CREATE_COMPLETE")
        b = make_state(status="UPDATE_COMPLETE")
        assert self._run(a, b) == 2

    def test_returns_1_when_both_missing(self, capsys):
        assert self._run(None, None) == 1
        out = capsys.readouterr().out
        assert "my-stack" in out

    def test_label_includes_region(self, capsys):
        s = make_state()
        self._run(s, s, region_a="us-east-1", region_b="eu-west-1")
        out = capsys.readouterr().out
        assert "us-east-1" in out
        assert "eu-west-1" in out

    def test_label_without_region(self, capsys):
        s = make_state()
        self._run(s, s)
        out = capsys.readouterr().out
        assert "dev" in out
        assert "prod" in out
