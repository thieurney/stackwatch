"""Tests for stackwatch.commands.lineage_cmd."""
from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.lineage_cmd import cmd_lineage, _fetch_raw_events
from stackwatch.fetcher import StackState


def _make_state(name: str = "my-stack") -> StackState:
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs={},
        capabilities=[],
        termination_protection=True,
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(
        stack="my-stack",
        region=None,
        profile=None,
        json_output=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def _ts(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)


def _make_event(ts, status, rtype="AWS::CloudFormation::Stack"):
    return {"Timestamp": ts, "ResourceStatus": status, "ResourceType": rtype}


def _run(args, state, events):
    with patch("stackwatch.commands.lineage_cmd.boto3.Session") as mock_session, \
         patch("stackwatch.commands.lineage_cmd.fetch_stack", return_value=state), \
         patch("stackwatch.commands.lineage_cmd._fetch_raw_events", return_value=events):
        return cmd_lineage(args)


def test_returns_1_when_stack_not_found():
    result = _run(_args(), None, [])
    assert result == 1


def test_returns_0_on_success(capsys):
    state = _make_state()
    events = [_make_event(_ts(2024, 1, 1), "CREATE_COMPLETE")]
    result = _run(_args(), state, events)
    assert result == 0
    captured = capsys.readouterr()
    assert "my-stack" in captured.out


def test_json_output_structure(capsys):
    import json
    state = _make_state()
    events = [
        _make_event(_ts(2024, 1, 1), "CREATE_COMPLETE"),
        _make_event(_ts(2024, 6, 1), "UPDATE_COMPLETE"),
    ]
    result = _run(_args(json_output=True), state, events)
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["stack_name"] == "my-stack"
    assert data["update_count"] == 1
    assert data["total_events"] == 2
    assert "age_days" in data


def test_json_output_no_events(capsys):
    import json
    state = _make_state()
    result = _run(_args(json_output=True), state, [])
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data["created_at"] is None
    assert data["age_days"] is None


def test_fetch_raw_events_paginates():
    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"StackEvents": [{"Timestamp": _ts(2024, 1, 1), "ResourceStatus": "CREATE_COMPLETE"}]},
        {"StackEvents": [{"Timestamp": _ts(2024, 2, 1), "ResourceStatus": "UPDATE_COMPLETE"}]},
    ]
    client.get_paginator.return_value = paginator
    events = _fetch_raw_events(client, "my-stack")
    assert len(events) == 2
