"""Tests for stackwatch.outputs."""
from __future__ import annotations

import pytest

from stackwatch.fetcher import StackState
from stackwatch.outputs import (
    OutputDiff,
    StackOutput,
    diff_outputs,
    has_output_changes,
    outputs_as_dict,
    parse_outputs,
)


def _state(outputs):
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        raw={"Outputs": outputs},
    )


def test_parse_outputs_empty():
    state = _state([])
    assert parse_outputs(state) == []


def test_parse_outputs_basic():
    state = _state(
        [
            {"OutputKey": "BucketName", "OutputValue": "my-bucket", "Description": "The bucket"},
            {"OutputKey": "Region", "OutputValue": "us-east-1"},
        ]
    )
    outputs = parse_outputs(state)
    assert len(outputs) == 2
    assert outputs[0] == StackOutput(key="BucketName", value="my-bucket", description="The bucket")
    assert outputs[1].export_name is None


def test_outputs_as_dict():
    state = _state(
        [{"OutputKey": "Url", "OutputValue": "https://example.com"}]
    )
    d = outputs_as_dict(state)
    assert d == {"Url": "https://example.com"}


def test_diff_outputs_no_change():
    state = _state([{"OutputKey": "K", "OutputValue": "v"}])
    assert diff_outputs(state, state) == []


def test_diff_outputs_value_changed():
    old = _state([{"OutputKey": "Url", "OutputValue": "http://old.example.com"}])
    new = _state([{"OutputKey": "Url", "OutputValue": "http://new.example.com"}])
    diffs = diff_outputs(old, new)
    assert len(diffs) == 1
    assert diffs[0] == OutputDiff(key="Url", old_value="http://old.example.com", new_value="http://new.example.com")


def test_diff_outputs_added():
    old = _state([])
    new = _state([{"OutputKey": "NewKey", "OutputValue": "val"}])
    diffs = diff_outputs(old, new)
    assert diffs == [OutputDiff(key="NewKey", old_value=None, new_value="val")]


def test_diff_outputs_removed():
    old = _state([{"OutputKey": "Gone", "OutputValue": "bye"}])
    new = _state([])
    diffs = diff_outputs(old, new)
    assert diffs == [OutputDiff(key="Gone", old_value="bye", new_value=None)]


def test_has_output_changes_true():
    old = _state([{"OutputKey": "X", "OutputValue": "1"}])
    new = _state([{"OutputKey": "X", "OutputValue": "2"}])
    assert has_output_changes(old, new) is True


def test_has_output_changes_false():
    state = _state([{"OutputKey": "X", "OutputValue": "1"}])
    assert has_output_changes(state, state) is False
