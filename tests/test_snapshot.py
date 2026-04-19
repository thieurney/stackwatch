"""Tests for stackwatch.snapshot module."""

import os
import pytest

from stackwatch.fetcher import StackState
from stackwatch.snapshot import save_snapshot, load_snapshot, list_snapshots


def make_state(name="my-stack") -> StackState:
    return StackState(
        stack_name=name,
        status="UPDATE_COMPLETE",
        parameters={"Env": "prod", "Count": "3"},
        outputs={"BucketName": "my-bucket"},
        tags={"Team": "platform"},
    )


def test_save_and_load_roundtrip(tmp_path):
    state = make_state()
    path = save_snapshot(state, label="baseline", directory=str(tmp_path))
    assert os.path.isfile(path)

    loaded = load_snapshot("my-stack", label="baseline", directory=str(tmp_path))
    assert loaded is not None
    assert loaded.stack_name == state.stack_name
    assert loaded.status == state.status
    assert loaded.parameters == state.parameters
    assert loaded.outputs == state.outputs
    assert loaded.tags == state.tags


def test_load_missing_returns_none(tmp_path):
    result = load_snapshot("ghost-stack", label="nope", directory=str(tmp_path))
    assert result is None


def test_save_creates_directory(tmp_path):
    subdir = str(tmp_path / "nested" / "dir")
    state = make_state()
    path = save_snapshot(state, label="v1", directory=subdir)
    assert os.path.isfile(path)


def test_list_snapshots_empty(tmp_path):
    assert list_snapshots(directory=str(tmp_path)) == []


def test_list_snapshots_nonexistent_dir(tmp_path):
    missing = str(tmp_path / "does_not_exist")
    assert list_snapshots(directory=missing) == []


def test_list_snapshots_returns_metadata(tmp_path):
    save_snapshot(make_state("stack-a"), label="v1", directory=str(tmp_path))
    save_snapshot(make_state("stack-b"), label="v2", directory=str(tmp_path))

    snapshots = list_snapshots(directory=str(tmp_path))
    assert len(snapshots) == 2
    names = {s["stack_name"] for s in snapshots}
    assert names == {"stack-a", "stack-b"}
    for s in snapshots:
        assert "saved_at" in s
        assert "label" in s
        assert "status" in s


def test_snapshot_filename_safe_chars(tmp_path):
    state = make_state("arn/my/stack")
    path = save_snapshot(state, label="env/prod", directory=str(tmp_path))
    assert "/" not in os.path.basename(path)
