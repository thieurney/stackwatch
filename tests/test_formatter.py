"""Tests for stackwatch.formatter."""

import pytest
from stackwatch.differ import FieldDiff, StackDiff
from stackwatch.formatter import format_field_diff, format_stack_diff, format_no_data


def make_diff(
    status=None, parameters=None, outputs=None
) -> StackDiff:
    return StackDiff(
        status=status,
        parameters=parameters or {},
        outputs=outputs or {},
    )


def test_format_field_diff_no_color():
    fd = FieldDiff(old_value="CREATE_COMPLETE", new_value="UPDATE_COMPLETE")
    result = format_field_diff("status", fd, use_color=False)
    assert "- 'CREATE_COMPLETE'" in result
    assert "+ 'UPDATE_COMPLETE'" in result
    assert "status:" in result


def test_format_field_diff_missing_old():
    fd = FieldDiff(old_value=None, new_value="value")
    result = format_field_diff("key", fd, use_color=False)
    assert "<missing>" in result
    assert "+ 'value'" in result


def test_format_stack_diff_no_changes():
    diff = make_diff()
    result = format_stack_diff(diff, "my-stack", use_color=False)
    assert "No differences found." in result
    assert "my-stack" in result


def test_format_stack_diff_status_change():
    diff = make_diff(status=FieldDiff("CREATE_COMPLETE", "UPDATE_COMPLETE"))
    result = format_stack_diff(diff, "my-stack", "prod", "staging", use_color=False)
    assert "[status]" in result
    assert "CREATE_COMPLETE" in result
    assert "UPDATE_COMPLETE" in result
    assert "prod" in result
    assert "staging" in result


def test_format_stack_diff_parameter_and_output():
    diff = make_diff(
        parameters={"Env": FieldDiff("prod", "dev")},
        outputs={"URL": FieldDiff("https://prod.example.com", "https://dev.example.com")},
    )
    result = format_stack_diff(diff, "my-stack", use_color=False)
    assert "[parameters]" in result
    assert "[outputs]" in result
    assert "Env:" in result
    assert "URL:" in result


def test_format_no_data():
    result = format_no_data("ghost-stack", "prod", use_color=False)
    assert "ghost-stack" in result
    assert "prod" in result


def test_format_uses_color_codes():
    fd = FieldDiff(old_value="a", new_value="b")
    result = format_field_diff("x", fd, use_color=True)
    assert "\033[" in result
