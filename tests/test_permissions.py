"""Tests for stackwatch.permissions."""
import json
import pytest

from stackwatch.permissions import (
    parse_permission_summary,
    format_permission_summary,
    IamCapability,
    PermissionSummary,
)


def _summary(**kwargs) -> PermissionSummary:
    defaults = dict(
        stack_name="my-stack",
        capabilities=[],
        resource_types=[],
    )
    defaults.update(kwargs)
    return parse_permission_summary(**defaults)


def test_parse_no_capabilities_no_iam():
    s = _summary()
    assert s.iam_capabilities == []
    assert not s.has_iam_resources
    assert s.warning is None


def test_parse_known_capability():
    s = _summary(capabilities=["CAPABILITY_IAM"])
    assert len(s.iam_capabilities) == 1
    assert s.iam_capabilities[0].name == "CAPABILITY_IAM"
    assert "IAM" in s.iam_capabilities[0].description


def test_parse_multiple_capabilities():
    caps = ["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"]
    s = _summary(capabilities=caps)
    names = [c.name for c in s.iam_capabilities]
    assert names == caps


def test_parse_unknown_capability_gets_default_description():
    s = _summary(capabilities=["CAPABILITY_UNKNOWN"])
    assert s.iam_capabilities[0].description == "Unknown capability."


def test_iam_resource_detected():
    s = _summary(resource_types=["AWS::IAM::Role", "AWS::S3::Bucket"])
    assert s.has_iam_resources is True


def test_sso_resource_detected():
    s = _summary(resource_types=["AWS::SSO::Assignment"])
    assert s.has_iam_resources is True


def test_warning_when_iam_resource_but_no_capability():
    s = _summary(resource_types=["AWS::IAM::Role"])
    assert s.warning is not None
    assert "IAM" in s.warning


def test_no_warning_when_capability_declared():
    s = _summary(capabilities=["CAPABILITY_IAM"], resource_types=["AWS::IAM::Role"])
    assert s.warning is None


def test_format_plain_no_color():
    s = _summary(capabilities=["CAPABILITY_IAM"], resource_types=["AWS::IAM::Role"])
    out = format_permission_summary(s, use_color=False)
    assert "my-stack" in out
    assert "CAPABILITY_IAM" in out
    assert "yes" in out


def test_format_plain_warning_no_color():
    s = _summary(resource_types=["AWS::IAM::Role"])
    out = format_permission_summary(s, use_color=False)
    assert "WARNING" in out
    assert "\033[" not in out


def test_format_json_structure():
    s = _summary(capabilities=["CAPABILITY_NAMED_IAM"], resource_types=["AWS::IAM::Policy"])
    out = format_permission_summary(s, as_json=True)
    data = json.loads(out)
    assert data["stack"] == "my-stack"
    assert data["iam_capabilities"][0]["name"] == "CAPABILITY_NAMED_IAM"
    assert data["has_iam_resources"] is True
