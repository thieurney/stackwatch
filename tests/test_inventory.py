"""Tests for stackwatch.inventory."""
from __future__ import annotations

from stackwatch.fetcher import StackState
from stackwatch.inventory import (
    InventoryRow,
    InventoryReport,
    build_inventory,
    format_inventory,
)


def _make_state(
    name: str = "my-stack",
    status: str = "CREATE_COMPLETE",
    params: dict | None = None,
    tags: dict | None = None,
    termination_protection: bool = False,
) -> StackState:
    raw = {"EnableTerminationProtection": termination_protection, "LastUpdatedTime": "2024-01-01"}
    return StackState(
        stack_name=name,
        status=status,
        parameters=params or {},
        tags=tags or {},
        raw=raw,
    )


# ---------------------------------------------------------------------------
# build_inventory
# ---------------------------------------------------------------------------

def test_build_inventory_empty():
    report = build_inventory([])
    assert report.total == 0
    assert report.protected_count == 0
    assert report.failed_count == 0


def test_build_inventory_skips_none():
    report = build_inventory([None, None])
    assert report.total == 0


def test_build_inventory_single_stack():
    state = _make_state("alpha", params={"Env": "prod"}, tags={"team": "ops"})
    report = build_inventory([state])
    assert report.total == 1
    row = report.rows[0]
    assert row.stack_name == "alpha"
    assert row.status == "CREATE_COMPLETE"
    assert row.parameter_count == 1
    assert row.tag_count == 1
    assert row.termination_protection is False
    assert row.last_updated == "2024-01-01"


def test_build_inventory_counts_protected():
    states = [
        _make_state("a", termination_protection=True),
        _make_state("b", termination_protection=False),
        _make_state("c", termination_protection=True),
    ]
    report = build_inventory(states)
    assert report.protected_count == 2


def test_build_inventory_counts_failed():
    states = [
        _make_state("a", status="CREATE_FAILED"),
        _make_state("b", status="ROLLBACK_COMPLETE"),
        _make_state("c", status="CREATE_COMPLETE"),
    ]
    report = build_inventory(states)
    assert report.failed_count == 2


def test_build_inventory_mixed_none_and_valid():
    states = [None, _make_state("x"), None, _make_state("y")]
    report = build_inventory(states)
    assert report.total == 2


# ---------------------------------------------------------------------------
# format_inventory
# ---------------------------------------------------------------------------

def test_format_inventory_no_stacks():
    report = InventoryReport(rows=[])
    assert format_inventory(report) == "No stacks found."


def test_format_inventory_contains_stack_name():
    state = _make_state("my-stack")
    report = build_inventory([state])
    output = format_inventory(report)
    assert "my-stack" in output


def test_format_inventory_contains_summary_line():
    states = [
        _make_state("a", termination_protection=True),
        _make_state("b", status="CREATE_FAILED"),
    ]
    report = build_inventory(states)
    output = format_inventory(report)
    assert "Total: 2" in output
    assert "Protected: 1" in output
    assert "Failed/Rollback: 1" in output
