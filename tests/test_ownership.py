"""Tests for stackwatch.ownership module."""
from __future__ import annotations

from stackwatch.fetcher import StackState
from stackwatch.ownership import (
    OwnershipInfo,
    build_ownership_info,
    format_ownership_info,
)


def _make_state(tags: dict) -> StackState:
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags=tags,
        outputs=[],
        capabilities=[],
        termination_protection=True,
        creation_time=None,
        last_updated_time=None,
        description=None,
        role_arn=None,
        notification_arns=[],
    )


def test_build_ownership_all_present():
    state = _make_state({"Owner": "alice", "Team": "platform", "CostCenter": "CC-42"})
    info = build_ownership_info(state)
    assert info.owner == "alice"
    assert info.team == "platform"
    assert info.cost_center == "CC-42"
    assert info.is_complete is True
    assert info.has_owner is True


def test_build_ownership_lowercase_keys():
    state = _make_state({"owner": "bob", "team": "data", "cost-center": "CC-99"})
    info = build_ownership_info(state)
    assert info.owner == "bob"
    assert info.team == "data"
    assert info.cost_center == "CC-99"


def test_build_ownership_missing_fields():
    state = _make_state({"Owner": "carol"})
    info = build_ownership_info(state)
    assert info.owner == "carol"
    assert info.team is None
    assert info.cost_center is None
    assert info.is_complete is False
    assert info.has_owner is True


def test_build_ownership_no_tags():
    state = _make_state({})
    info = build_ownership_info(state)
    assert info.owner is None
    assert info.team is None
    assert info.cost_center is None
    assert info.has_owner is False
    assert info.is_complete is False


def test_format_ownership_plain_no_color():
    info = OwnershipInfo(
        stack_name="demo",
        owner="alice",
        team="platform",
        cost_center="CC-1",
    )
    out = format_ownership_info(info, use_color=False)
    assert "demo" in out
    assert "alice" in out
    assert "platform" in out
    assert "CC-1" in out


def test_format_ownership_unset_shown():
    info = OwnershipInfo(stack_name="demo", owner=None, team=None, cost_center=None)
    out = format_ownership_info(info, use_color=False)
    assert "(unset)" in out


def test_raw_tags_stored():
    state = _make_state({"Owner": "x", "Env": "prod"})
    info = build_ownership_info(state)
    assert info.raw_tags["Env"] == "prod"
