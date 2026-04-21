"""Unit tests for NotificationConfig dataclass helpers."""
from __future__ import annotations

import json

import pytest

from stackwatch.commands.notifications_cmd import NotificationConfig, _format_notifications


def _arn(name: str) -> str:
    return f"arn:aws:sns:eu-west-1:999999999999:{name}"


def test_topic_name_last_segment():
    c = NotificationConfig(topic_arn=_arn("deploy-alerts"))
    assert c.topic_name == "deploy-alerts"


def test_topic_name_with_hyphens():
    c = NotificationConfig(topic_arn=_arn("prod-critical-alerts"))
    assert c.topic_name == "prod-critical-alerts"


def test_format_empty_list_json():
    result = _format_notifications([], use_json=True)
    assert json.loads(result) == []


def test_format_multiple_plain():
    configs = [
        NotificationConfig(topic_arn=_arn("topic-one")),
        NotificationConfig(topic_arn=_arn("topic-two")),
    ]
    output = _format_notifications(configs, use_json=False)
    assert "topic-one" in output
    assert "topic-two" in output


def test_format_multiple_json():
    configs = [
        NotificationConfig(topic_arn=_arn("alpha")),
        NotificationConfig(topic_arn=_arn("beta")),
    ]
    output = _format_notifications(configs, use_json=True)
    data = json.loads(output)
    assert len(data) == 2
    names = {d["topic_name"] for d in data}
    assert names == {"alpha", "beta"}


def test_format_json_includes_full_arn():
    arn = _arn("my-topic")
    configs = [NotificationConfig(topic_arn=arn)]
    data = json.loads(_format_notifications(configs, use_json=True))
    assert data[0]["topic_arn"] == arn
