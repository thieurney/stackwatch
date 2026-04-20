from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.events_cmd import cmd_events, _fetch_events
from stackwatch.fetcher import StackState


def _make_state(name="my-stack"):
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
        region="us-east-1",
    )


def _args(**kwargs):
    defaults = dict(
        stack="my-stack",
        region=None,
        profile=None,
        limit=20,
        as_json=False,
        filter_status=None,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def _make_event(logical_id="MyBucket", status="CREATE_COMPLETE", reason=""):
    return {
        "Timestamp": datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        "LogicalResourceId": logical_id,
        "ResourceStatus": status,
        "ResourceStatusReason": reason,
    }


def test_returns_1_when_stack_not_found(capsys):
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=None):
        result = cmd_events(_args())
    assert result == 1
    out = capsys.readouterr().out
    assert "my-stack" in out


def test_returns_0_with_no_events(capsys):
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.events_cmd._fetch_events", return_value=[]):
        result = cmd_events(_args())
    assert result == 0
    assert "No events found" in capsys.readouterr().out


def test_text_output_contains_event_fields(capsys):
    events = [_make_event("MyBucket", "CREATE_COMPLETE", "")]
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.events_cmd._fetch_events", return_value=events):
        result = cmd_events(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "MyBucket" in out
    assert "CREATE_COMPLETE" in out


def test_json_output_structure(capsys):
    import json
    events = [_make_event("MyBucket", "UPDATE_FAILED", "Resource error")]
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.events_cmd._fetch_events", return_value=events):
        result = cmd_events(_args(as_json=True))
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["logical_id"] == "MyBucket"
    assert data[0]["status"] == "UPDATE_FAILED"
    assert data[0]["reason"] == "Resource error"


def test_filter_status_excludes_non_matching(capsys):
    events = [
        _make_event("BucketA", "CREATE_COMPLETE"),
        _make_event("BucketB", "UPDATE_FAILED", "oops"),
    ]
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.events_cmd._fetch_events", return_value=events):
        result = cmd_events(_args(filter_status="FAILED"))
    assert result == 0
    out = capsys.readouterr().out
    assert "BucketB" in out
    assert "BucketA" not in out


def test_reason_shown_in_text_output(capsys):
    events = [_make_event("Res", "CREATE_FAILED", "Limit exceeded")]
    with patch("stackwatch.commands.events_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.events_cmd._fetch_events", return_value=events):
        cmd_events(_args())
    out = capsys.readouterr().out
    assert "Limit exceeded" in out
