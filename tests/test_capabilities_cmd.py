from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.capabilities_cmd import (
    CapabilityInfo,
    _fetch_capabilities,
    _format_capabilities,
    cmd_capabilities,
)
from stackwatch.fetcher import StackState


def _make_state(name="my-stack"):
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
    )


def _args(**kwargs):
    defaults = dict(stack="my-stack", region=None, profile=None, use_json=False)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# --- _format_capabilities ---

def test_format_empty_plain():
    result = _format_capabilities([], use_json=False)
    assert result == "  (none)"


def test_format_single_plain():
    caps = [CapabilityInfo("CAPABILITY_IAM", "Allows creation of IAM resources (roles, policies, users).")]
    result = _format_capabilities(caps, use_json=False)
    assert "CAPABILITY_IAM" in result
    assert "Allows creation of IAM resources" in result


def test_format_json_output():
    caps = [
        CapabilityInfo("CAPABILITY_IAM", "desc1"),
        CapabilityInfo("CAPABILITY_NAMED_IAM", "desc2"),
    ]
    result = _format_capabilities(caps, use_json=True)
    import json
    data = json.loads(result)
    assert len(data) == 2
    assert data[0]["capability"] == "CAPABILITY_IAM"
    assert data[1]["description"] == "desc2"


# --- cmd_capabilities ---

def test_returns_1_when_stack_not_found():
    session = MagicMock()
    with patch("stackwatch.commands.capabilities_cmd.fetch_stack", return_value=None):
        code = cmd_capabilities(_args(), session=session)
    assert code == 1


def test_returns_0_with_no_capabilities(capsys):
    session = MagicMock()
    cf_client = MagicMock()
    cf_client.describe_stacks.return_value = {
        "Stacks": [{"Capabilities": []}]
    }
    session.client.return_value = cf_client

    with patch("stackwatch.commands.capabilities_cmd.fetch_stack", return_value=_make_state()):
        code = cmd_capabilities(_args(), session=session)

    assert code == 0
    out = capsys.readouterr().out
    assert "(none)" in out


def test_returns_0_with_capabilities(capsys):
    session = MagicMock()
    cf_client = MagicMock()
    cf_client.describe_stacks.return_value = {
        "Stacks": [{"Capabilities": ["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"]}]
    }
    session.client.return_value = cf_client

    with patch("stackwatch.commands.capabilities_cmd.fetch_stack", return_value=_make_state()):
        code = cmd_capabilities(_args(), session=session)

    assert code == 0
    out = capsys.readouterr().out
    assert "CAPABILITY_IAM" in out
    assert "CAPABILITY_AUTO_EXPAND" in out


def test_json_flag_produces_json(capsys):
    session = MagicMock()
    cf_client = MagicMock()
    cf_client.describe_stacks.return_value = {
        "Stacks": [{"Capabilities": ["CAPABILITY_NAMED_IAM"]}]
    }
    session.client.return_value = cf_client

    with patch("stackwatch.commands.capabilities_cmd.fetch_stack", return_value=_make_state()):
        code = cmd_capabilities(_args(use_json=True), session=session)

    assert code == 0
    out = capsys.readouterr().out
    import json
    # extract JSON portion from output (second line onward)
    json_part = "[" + out.split("[", 1)[1]
    data = json.loads(json_part)
    assert data[0]["capability"] == "CAPABILITY_NAMED_IAM"
