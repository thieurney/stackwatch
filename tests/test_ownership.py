"""Tests for stackwatch.ownership."""
from stackwatch.fetcher import StackState
from stackwatch.ownership import (
    OwnershipInfo,
    build_ownership_info,
    format_ownership_plain,
)


def _make_state(tags: dict | None = None) -> StackState:
    return StackState(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags=tags or {},
        outputs=[],
        capabilities=[],
        termination_protection=False,
        creation_time=None,
        last_updated=None,
        description="",
    )


def test_no_tags_returns_unowned():
    info = build_ownership_info(_make_state())
    assert info.owner is None
    assert info.team is None
    assert info.environment is None
    assert not info.is_owned


def test_owner_tag_detected():
    info = build_ownership_info(_make_state({"Owner": "alice"}))
    assert info.owner == "alice"
    assert info.is_owned


def test_lowercase_owner_tag_detected():
    info = build_ownership_info(_make_state({"owner": "bob"}))
    assert info.owner == "bob"


def test_team_tag_detected():
    info = build_ownership_info(_make_state({"Team": "platform"}))
    assert info.team == "platform"
    assert info.is_owned


def test_env_tag_detected():
    info = build_ownership_info(_make_state({"Environment": "production"}))
    assert info.environment == "production"


def test_extra_tags_captured():
    info = build_ownership_info(_make_state({"Owner": "alice", "CostCenter": "cc-42"}))
    assert info.extra_tags == {"CostCenter": "cc-42"}


def test_format_plain_owned():
    info = OwnershipInfo(
        stack_name="svc-stack",
        owner="carol",
        team="backend",
        environment="staging",
    )
    out = format_ownership_plain(info)
    assert "carol" in out
    assert "backend" in out
    assert "staging" in out
    assert "WARNING" not in out


def test_format_plain_unowned_shows_warning():
    info = OwnershipInfo(stack_name="orphan")
    out = format_ownership_plain(info)
    assert "WARNING" in out
    assert "(unset)" in out


def test_format_plain_extra_tags_shown():
    info = OwnershipInfo(
        stack_name="svc",
        owner="dave",
        extra_tags={"CostCenter": "cc-99"},
    )
    out = format_ownership_plain(info)
    assert "CostCenter" in out
    assert "cc-99" in out
