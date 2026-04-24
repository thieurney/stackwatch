"""Tests for stackwatch.lineage."""
from datetime import datetime, timezone

import pytest

from stackwatch.lineage import (
    LineageEvent,
    StackLineage,
    build_lineage,
    format_lineage,
)


def _ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


def _event(ts: datetime, status: str, rtype: str = "AWS::CloudFormation::Stack") -> dict:
    return {
        "Timestamp": ts,
        "ResourceStatus": status,
        "ResourceType": rtype,
    }


def test_build_lineage_empty():
    lineage = build_lineage("my-stack", [])
    assert lineage.stack_name == "my-stack"
    assert lineage.created_at is None
    assert lineage.last_updated_at is None
    assert lineage.events == []


def test_build_lineage_single_event():
    ts = _ts(2024, 1, 10)
    lineage = build_lineage("my-stack", [_event(ts, "CREATE_COMPLETE")])
    assert lineage.created_at == ts
    assert lineage.last_updated_at is None


def test_build_lineage_multiple_events_sorted():
    t1 = _ts(2024, 1, 10)
    t2 = _ts(2024, 3, 5)
    t3 = _ts(2024, 6, 1)
    raw = [_event(t3, "UPDATE_COMPLETE"), _event(t1, "CREATE_COMPLETE"), _event(t2, "UPDATE_COMPLETE")]
    lineage = build_lineage("my-stack", raw)
    assert lineage.created_at == t1
    assert lineage.last_updated_at == t3
    assert lineage.update_count == 2


def test_build_lineage_ignores_non_stack_resources():
    ts = _ts(2024, 1, 10)
    raw = [
        _event(ts, "CREATE_COMPLETE"),
        {"Timestamp": ts, "ResourceStatus": "CREATE_COMPLETE", "ResourceType": "AWS::S3::Bucket"},
    ]
    lineage = build_lineage("my-stack", raw)
    assert len(lineage.events) == 1


def test_age_days_none_when_no_created_at():
    lineage = StackLineage(stack_name="x", created_at=None, last_updated_at=None)
    assert lineage.age_days is None


def test_age_days_positive():
    ts = _ts(2020, 1, 1)
    lineage = StackLineage(stack_name="x", created_at=ts, last_updated_at=None)
    assert lineage.age_days > 0


def test_format_lineage_contains_stack_name():
    ts = _ts(2024, 1, 1)
    lineage = StackLineage(stack_name="prod-stack", created_at=ts, last_updated_at=None)
    output = format_lineage(lineage)
    assert "prod-stack" in output
    assert "2024-01-01" in output
    assert "Updates" in output


def test_format_lineage_unknown_when_no_created():
    lineage = StackLineage(stack_name="x", created_at=None, last_updated_at=None)
    output = format_lineage(lineage)
    assert "unknown" in output
