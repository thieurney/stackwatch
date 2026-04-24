"""Tests for stackwatch.rollup."""
import json
import pytest

from stackwatch.fetcher import StackState
from stackwatch.rollup import (
    RollupReport,
    StackRollupRow,
    _is_failed,
    build_rollup,
    format_rollup,
)


def _make_state(name="MyStack", status="CREATE_COMPLETE", region="us-east-1", params=None, tags=None, raw=None):
    return StackState(
        name=name,
        status=status,
        region=region,
        parameters=params or {},
        tags=tags or {},
        raw=raw or {},
    )


def test_is_failed_on_rollback_complete():
    assert _is_failed("ROLLBACK_COMPLETE") is True


def test_is_failed_on_create_failed():
    assert _is_failed("CREATE_FAILED") is True


def test_is_failed_false_for_complete():
    assert _is_failed("CREATE_COMPLETE") is False


def test_build_rollup_empty():
    report = build_rollup([])
    assert report.total == 0
    assert report.healthy == 0
    assert report.failed == 0
    assert report.failure_rate == 0.0


def test_build_rollup_counts_correctly():
    states = [
        _make_state("A", "CREATE_COMPLETE"),
        _make_state("B", "ROLLBACK_COMPLETE"),
        _make_state("C", "UPDATE_COMPLETE"),
    ]
    report = build_rollup(states)
    assert report.total == 3
    assert report.healthy == 2
    assert report.failed == 1
    assert report.failure_rate == 33.3


def test_build_rollup_row_fields():
    state = _make_state(
        "MyStack",
        params={"Env": "prod"},
        tags={"Team": "platform", "Project": "x"},
        raw={"DriftInformation": {"StackDriftStatus": "DRIFTED"}},
    )
    report = build_rollup([state])
    row = report.rows[0]
    assert row.name == "MyStack"
    assert row.parameter_count == 1
    assert row.tag_count == 2
    assert row.drift_status == "DRIFTED"


def test_format_rollup_plain_contains_header():
    report = build_rollup([_make_state()])
    output = format_rollup(report, color=False)
    assert "Name" in output
    assert "MyStack" in output


def test_format_rollup_json_structure():
    states = [_make_state("A"), _make_state("B", "CREATE_FAILED")]
    report = build_rollup(states)
    output = format_rollup(report, fmt="json")
    data = json.loads(output)
    assert data["total"] == 2
    assert data["failed"] == 1
    assert len(data["stacks"]) == 2


def test_format_rollup_plain_failure_rate():
    states = [_make_state("A", "ROLLBACK_COMPLETE")]
    report = build_rollup(states)
    output = format_rollup(report, color=False)
    assert "100.0%" in output
