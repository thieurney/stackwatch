"""Tests for stackwatch.differ module."""

import pytest
from stackwatch.fetcher import StackState
from stackwatch.differ import diff_stacks, FieldDiff


def make_state(**kwargs) -> StackState:
    defaults = dict(
        name="my-stack",
        status="UPDATE_COMPLETE",
        region="us-east-1",
        parameters={},
        outputs={},
        tags={},
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def test_no_diff():
    left = make_state(parameters={"Env": "prod"}, outputs={"URL": "https://example.com"})
    right = make_state(parameters={"Env": "prod"}, outputs={"URL": "https://example.com"})
    result = diff_stacks(left, right, "staging", "prod")
    assert not result.has_changes


def test_status_diff():
    left = make_state(status="UPDATE_COMPLETE")
    right = make_state(status="UPDATE_ROLLBACK_COMPLETE")
    result = diff_stacks(left, right, "staging", "prod")
    assert result.has_changes
    assert len(result.status_diff) == 1
    assert result.status_diff[0] == FieldDiff(key="status", left="UPDATE_COMPLETE", right="UPDATE_ROLLBACK_COMPLETE")


def test_parameter_diff():
    left = make_state(parameters={"InstanceType": "t3.small", "Count": "2"})
    right = make_state(parameters={"InstanceType": "t3.medium", "Count": "2"})
    result = diff_stacks(left, right, "dev", "prod")
    assert result.has_changes
    assert len(result.parameter_diffs) == 1
    assert result.parameter_diffs[0].key == "InstanceType"
    assert result.parameter_diffs[0].left == "t3.small"
    assert result.parameter_diffs[0].right == "t3.medium"


def test_missing_key_in_one_side():
    left = make_state(parameters={"FeatureFlag": "true"})
    right = make_state(parameters={})
    result = diff_stacks(left, right, "staging", "prod")
    assert result.has_changes
    assert result.parameter_diffs[0].right == "<missing>"


def test_tag_diff():
    left = make_state(tags={"Owner": "team-a"})
    right = make_state(tags={"Owner": "team-b"})
    result = diff_stacks(left, right, "dev", "prod")
    assert len(result.tag_diffs) == 1
