"""Tests for stackwatch.deprecation module."""
from __future__ import annotations

import pytest

from stackwatch.deprecation import (
    DeprecationReport,
    DeprecationWarning,
    _check_no_tags,
    _check_parameters,
    _check_status,
    build_deprecation_report,
    format_deprecation_report,
)
from stackwatch.fetcher import StackState


def _make_state(
    status: str = "CREATE_COMPLETE",
    parameters: dict | None = None,
    tags: dict | None = None,
) -> StackState:
    return StackState(
        name="my-stack",
        status=status,
        parameters=parameters or {"Env": "prod"},
        tags=tags or {"Team": "platform"},
    )


# --- _check_status ---

def test_check_status_clean_returns_empty():
    state = _make_state(status="CREATE_COMPLETE")
    assert _check_status(state) == []


def test_check_status_rollback_complete_is_high():
    state = _make_state(status="ROLLBACK_COMPLETE")
    warnings = _check_status(state)
    assert len(warnings) == 1
    assert warnings[0].severity == "high"
    assert warnings[0].code == "DEPRECATED_STATUS"


def test_check_status_delete_failed_is_high():
    state = _make_state(status="DELETE_FAILED")
    warnings = _check_status(state)
    assert warnings[0].severity == "high"


# --- _check_parameters ---

def test_check_parameters_no_hints_returns_empty():
    state = _make_state(parameters={"VpcId": "vpc-123", "Env": "prod"})
    assert _check_parameters(state) == []


def test_check_parameters_detects_legacy_mode():
    state = _make_state(parameters={"LegacyMode": "true"})
    warnings = _check_parameters(state)
    assert len(warnings) == 1
    assert warnings[0].code == "DEPRECATED_PARAM"
    assert warnings[0].severity == "medium"


def test_check_parameters_case_insensitive_hint():
    state = _make_state(parameters={"OldVpcCidr": "10.0.0.0/16"})
    warnings = _check_parameters(state)
    assert any(w.code == "DEPRECATED_PARAM" for w in warnings)


# --- _check_no_tags ---

def test_check_no_tags_with_tags_returns_empty():
    state = _make_state(tags={"Env": "prod"})
    assert _check_no_tags(state) == []


def test_check_no_tags_without_tags_returns_low_warning():
    state = _make_state(tags={})
    warnings = _check_no_tags(state)
    assert len(warnings) == 1
    assert warnings[0].severity == "low"
    assert warnings[0].code == "NO_TAGS"


# --- build_deprecation_report ---

def test_build_report_clean_stack_has_no_warnings():
    state = _make_state()
    report = build_deprecation_report(state)
    assert not report.has_warnings
    assert report.high_count == 0


def test_build_report_accumulates_all_checks():
    state = _make_state(status="ROLLBACK_COMPLETE", parameters={"LegacyMode": "1"}, tags={})
    report = build_deprecation_report(state)
    assert report.has_warnings
    codes = {w.code for w in report.warnings}
    assert "DEPRECATED_STATUS" in codes
    assert "DEPRECATED_PARAM" in codes
    assert "NO_TAGS" in codes


# --- format_deprecation_report ---

def test_format_no_warnings_returns_clean_message():
    report = DeprecationReport(stack_name="my-stack", warnings=[])
    out = format_deprecation_report(report)
    assert "no deprecation warnings" in out


def test_format_with_warnings_lists_them():
    report = DeprecationReport(
        stack_name="my-stack",
        warnings=[
            DeprecationWarning(code="DEPRECATED_STATUS", message="bad status", severity="high")
        ],
    )
    out = format_deprecation_report(report, color=False)
    assert "DEPRECATED_STATUS" in out
    assert "[HIGH]" in out


def test_format_color_adds_escape_codes():
    report = DeprecationReport(
        stack_name="my-stack",
        warnings=[
            DeprecationWarning(code="NO_TAGS", message="no tags", severity="low")
        ],
    )
    out = format_deprecation_report(report, color=True)
    assert "\033[" in out
