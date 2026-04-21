"""Unit tests for stackwatch.validation."""
from __future__ import annotations

import pytest

from stackwatch.validation import (
    TemplateParameter,
    ValidationResult,
    format_validation_result,
    parse_validation_response,
)


def _raw_response(**kwargs):
    base = {
        "Parameters": [],
        "Description": "",
        "Capabilities": [],
        "CapabilitiesReason": "",
    }
    base.update(kwargs)
    return base


def test_parse_empty_response():
    result = parse_validation_response(_raw_response())
    assert result.valid is True
    assert result.parameters == []
    assert result.capabilities == []
    assert result.description == ""


def test_parse_with_parameters():
    raw = _raw_response(
        Parameters=[
            {"ParameterKey": "Env", "DefaultValue": "dev", "NoEcho": False},
            {"ParameterKey": "Secret", "NoEcho": True},
        ]
    )
    result = parse_validation_response(raw)
    assert len(result.parameters) == 2
    assert result.parameters[0].key == "Env"
    assert result.parameters[0].default_value == "dev"
    assert result.parameters[1].no_echo is True


def test_parse_with_capabilities():
    raw = _raw_response(
        Capabilities=["CAPABILITY_IAM"],
        CapabilitiesReason="Template includes IAM resources.",
    )
    result = parse_validation_response(raw)
    assert result.capabilities == ["CAPABILITY_IAM"]
    assert "IAM" in result.capabilities_reason


def test_format_valid_no_color():
    result = ValidationResult(valid=True, description="My stack")
    text = format_validation_result(result, color=False)
    assert "✓" in text
    assert "valid" in text
    assert "My stack" in text


def test_format_invalid_no_color():
    result = ValidationResult(valid=False, error_message="Unresolved resource")
    text = format_validation_result(result, color=False)
    assert "✗" in text
    assert "Unresolved resource" in text


def test_format_includes_parameters():
    result = ValidationResult(
        valid=True,
        parameters=[
            TemplateParameter(key="BucketName", default_value="my-bucket"),
            TemplateParameter(key="Password", no_echo=True),
        ],
    )
    text = format_validation_result(result, color=False)
    assert "BucketName" in text
    assert "my-bucket" in text
    assert "[NoEcho]" in text


def test_format_with_color_uses_escape():
    result = ValidationResult(valid=True)
    text = format_validation_result(result, color=True)
    assert "\033[" in text
