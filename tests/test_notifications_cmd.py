"""Tests for notifications_cmd."""
from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.notifications_cmd import (
    NotificationConfig,
    _fetch_notifications,
    _format_notifications,
    cmd_notifications,
)
from stackwatch.fetcher import StackState


def _make_state(name="my-stack") -> StackState:
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        outputs={},
        tags={},
        region="us-east-1",
    )


def _args(**kwargs) -> Namespace:
    defaults = dict(
        stack="my-stack",
        region="us-east-1",
        profile=None,
        use_json=False,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.notifications_cmd.fetch_stack", return_value=None):
        result = cmd_notifications(_args())
    assert result == 1


def test_returns_0_when_no_notifications(capsys):
    with patch("stackwatch.commands.notifications_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.notifications_cmd._fetch_notifications", return_value=[]):
        result = cmd_notifications(_args())
    assert result == 0
    captured = capsys.readouterr()
    assert "No notification" in captured.out


def test_returns_0_with_notifications(capsys):
    configs = [
        NotificationConfig(topic_arn="arn:aws:sns:us-east-1:123456789012:my-topic"),
    ]
    with patch("stackwatch.commands.notifications_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.notifications_cmd._fetch_notifications", return_value=configs):
        result = cmd_notifications(_args())
    assert result == 0
    captured = capsys.readouterr()
    assert "my-topic" in captured.out


def test_json_output(capsys):
    import json
    configs = [
        NotificationConfig(topic_arn="arn:aws:sns:us-east-1:123456789012:alerts"),
    ]
    with patch("stackwatch.commands.notifications_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.notifications_cmd._fetch_notifications", return_value=configs):
        result = cmd_notifications(_args(use_json=True))
    assert result == 0
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    json_str = "\n".join(lines[1:])  # skip header line
    data = json.loads(json_str)
    assert data[0]["topic_name"] == "alerts"


def test_topic_name_property():
    c = NotificationConfig(topic_arn="arn:aws:sns:us-east-1:123456789012:my-topic")
    assert c.topic_name == "my-topic"


def test_format_notifications_plain():
    configs = [NotificationConfig(topic_arn="arn:aws:sns:us-east-1:000000000000:test-topic")]
    output = _format_notifications(configs, use_json=False)
    assert "arn:aws:sns" in output
    assert "test-topic" in output


def test_fetch_notifications_parses_arns():
    mock_client = MagicMock()
    mock_client.describe_stacks.return_value = {
        "Stacks": [
            {"NotificationARNs": ["arn:aws:sns:us-east-1:123:topic-a", "arn:aws:sns:us-east-1:123:topic-b"]}
        ]
    }
    with patch("boto3.client", return_value=mock_client):
        results = _fetch_notifications("my-stack", "us-east-1")
    assert len(results) == 2
    assert results[0].topic_name == "topic-a"
