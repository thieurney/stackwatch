"""Tests for cost_cmd."""
from __future__ import annotations

import json
import argparse
from unittest.mock import patch, MagicMock

import pytest

from stackwatch.commands.cost_cmd import cmd_cost, add_cost_subcommand
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack", cost_url: str | None = None) -> StackState:
    s = StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )
    if cost_url is not None:
        object.__setattr__(s, "cost_estimation_url", cost_url)
    return s


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(stack="my-stack", region="us-east-1", profile=None, as_json=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.cost_cmd.fetch_stack", return_value=None):
        assert cmd_cost(_args()) == 1


def test_returns_0_when_stack_found(capsys):
    state = _make_state()
    with patch("stackwatch.commands.cost_cmd.fetch_stack", return_value=state):
        result = cmd_cost(_args())
    assert result == 0


def test_no_cost_url_prints_tip(capsys):
    state = _make_state(cost_url=None)
    with patch("stackwatch.commands.cost_cmd.fetch_stack", return_value=state):
        cmd_cost(_args())
    out = capsys.readouterr().out
    assert "estimate-template-cost" in out


def test_cost_url_is_printed(capsys):
    state = _make_state(cost_url="https://aws.amazon.com/cost?token=abc")
    with patch("stackwatch.commands.cost_cmd.fetch_stack", return_value=state):
        cmd_cost(_args())
    out = capsys.readouterr().out
    assert "https://aws.amazon.com/cost?token=abc" in out


def test_json_output_structure(capsys):
    state = _make_state(cost_url="https://example.com")
    with patch("stackwatch.commands.cost_cmd.fetch_stack", return_value=state):
        cmd_cost(_args(as_json=True))
    data = json.loads(capsys.readouterr().out)
    assert data["stack"] == "my-stack"
    assert "cost_estimation_url" in data


def test_add_cost_subcommand_registers():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    add_cost_subcommand(sub)
    args = parser.parse_args(["cost", "my-stack", "--region", "eu-west-1"])
    assert args.stack == "my-stack"
    assert args.region == "eu-west-1"
    assert args.func is cmd_cost
