"""Tests for stackwatch.commands.tag_cmd."""
from __future__ import annotations

import argparse
import io
from unittest.mock import patch

import pytest

from stackwatch.commands.tag_cmd import cmd_tags, _parse_tag_filter
from stackwatch.fetcher import StackState


def _make_state(tags=None):
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags=tags or {},
    )


def _args(**kwargs):
    defaults = dict(stack="my-stack", env="default", region=None, tag_filter=None)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- _parse_tag_filter ---

def test_parse_tag_filter_none():
    assert _parse_tag_filter(None) is None


def test_parse_tag_filter_valid():
    assert _parse_tag_filter("Env=prod") == ("Env", "prod")


def test_parse_tag_filter_invalid():
    with pytest.raises(ValueError, match="KEY=VALUE"):
        _parse_tag_filter("badvalue")


# --- cmd_tags ---

def _run(args, state):
    out = io.StringIO()
    with patch("stackwatch.commands.tag_cmd.fetch_stack", return_value=state):
        code = cmd_tags(args, out=out)
    return code, out.getvalue()


def test_stack_not_found():
    code, text = _run(_args(), None)
    assert code == 1
    assert "no data" in text.lower() or "my-stack" in text


def test_no_tags():
    code, text = _run(_args(), _make_state(tags={}))
    assert code == 0
    assert "no tags" in text


def test_lists_tags():
    code, text = _run(_args(), _make_state(tags={"Env": "prod", "Team": "platform"}))
    assert code == 0
    assert "Env = prod" in text
    assert "Team = platform" in text


def test_filter_match():
    code, text = _run(_args(tag_filter="Env=prod"), _make_state(tags={"Env": "prod"}))
    assert code == 0
    assert "matches" in text


def test_filter_no_match():
    code, text = _run(_args(tag_filter="Env=staging"), _make_state(tags={"Env": "prod"}))
    assert code == 1
    assert "does not match" in text


def test_invalid_filter_returns_1():
    out = io.StringIO()
    with patch("stackwatch.commands.tag_cmd.fetch_stack", return_value=_make_state()):
        code = cmd_tags(_args(tag_filter="badfilter"), out=out)
    assert code == 1
    assert "Error" in out.getvalue()
