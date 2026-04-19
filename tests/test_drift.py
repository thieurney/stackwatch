import pytest
from stackwatch.drift import parse_drift_summary, format_drift_summary, DriftSummary, ResourceDrift


RAW_DRIFTED = {
    "StackResourceDrifts": [
        {
            "LogicalResourceId": "MyBucket",
            "ResourceType": "AWS::S3::Bucket",
            "StackResourceDriftStatus": "MODIFIED",
            "PropertyDifferences": [
                {"PropertyPath": "/VersioningConfiguration/Status"},
            ],
        },
        {
            "LogicalResourceId": "MyTable",
            "ResourceType": "AWS::DynamoDB::Table",
            "StackResourceDriftStatus": "NOT_CHECKED",
            "PropertyDifferences": [],
        },
    ]
}


def test_parse_drifted():
    summary = parse_drift_summary("my-stack", RAW_DRIFTED)
    assert summary.stack_name == "my-stack"
    assert summary.drift_status == "DRIFTED"
    assert summary.drifted_count == 1
    assert len(summary.resources) == 2


def test_parse_empty_returns_not_checked():
    summary = parse_drift_summary("empty-stack", {})
    assert summary.drift_status == "NOT_CHECKED"
    assert summary.drifted_count == 0


def test_parse_all_in_sync():
    raw = {
        "StackResourceDrifts": [
            {
                "LogicalResourceId": "Fn",
                "ResourceType": "AWS::Lambda::Function",
                "StackResourceDriftStatus": "IN_SYNC",
                "PropertyDifferences": [],
            }
        ]
    }
    summary = parse_drift_summary("stack", raw)
    assert summary.drift_status == "IN_SYNC"
    assert summary.drifted_count == 0


def test_is_drifted_property():
    s = DriftSummary(stack_name="x", drift_status="DRIFTED", drifted_count=1)
    assert s.is_drifted is True
    s2 = DriftSummary(stack_name="x", drift_status="IN_SYNC")
    assert s2.is_drifted is False


def test_format_includes_resource_details():
    summary = parse_drift_summary("my-stack", RAW_DRIFTED)
    lines = format_drift_summary(summary)
    joined = "\n".join(lines)
    assert "my-stack" in joined
    assert "DRIFTED" in joined
    assert "MyBucket" in joined
    assert "/VersioningConfiguration/Status" in joined


def test_format_skips_non_drifted_resources():
    summary = parse_drift_summary("my-stack", RAW_DRIFTED)
    lines = format_drift_summary(summary)
    joined = "\n".join(lines)
    assert "MyTable" not in joined
