"""Tests for stackwatch.commands.resources_cmd."""
from __future__ import annotations

import argparse
import json
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.resources_cmd import (
    StackResource,
    _fetch_resources,
    cmd_resources,
)


def _make_resource(logical_id="MyBucket", physical_id="my-bucket-123",
                   resource_type="AWS::S3::Bucket", status="CREATE_COMPLETE"):
    return StackResource(
        logical_id=logical_id,
        physical_id=physical_id,
        resource_type=resource_type,
        status=status,
    )


def _args(**kwargs):
    defaults = dict(stack="my-stack", region="us-east-1",
                    filter_type=None, output_json=False)
    defaults.update(kwargs)
    ns = argparse.Namespace(**defaults)
    ns.func = cmd_resources
    return ns


def _make_paginator_response(resources: List[StackResource]):
    """Build a mock paginator that yields a single page."""
    page = {
        "StackResourceSummaries": [
            {
                "LogicalResourceId": r.logical_id,
                "PhysicalResourceId": r.physical_id,
                "ResourceType": r.resource_type,
                "ResourceStatus": r.status,
            }
            for r in resources
        ]
    }
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [page]
    return mock_paginator


@patch("stackwatch.commands.resources_cmd.boto3.client")
def test_returns_1_when_stack_not_found(mock_boto, capsys):
    client = MagicMock()
    err = client.exceptions.ClientError
    err = type("ClientError", (Exception,), {})
    client.exceptions.ClientError = err
    client.get_paginator.side_effect = err("Stack does not exist")
    mock_boto.return_value = client

    result = cmd_resources(_args())
    assert result == 1
    out = capsys.readouterr().out
    assert "not found" in out


@patch("stackwatch.commands.resources_cmd.boto3.client")
def test_returns_0_with_resources(mock_boto, capsys):
    resources = [_make_resource(), _make_resource("MyQueue", "https://sqs...",
                                                   "AWS::SQS::Queue", "CREATE_COMPLETE")]
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator_response(resources)
    mock_boto.return_value = client

    result = cmd_resources(_args())
    assert result == 0
    out = capsys.readouterr().out
    assert "MyBucket" in out
    assert "MyQueue" in out


@patch("stackwatch.commands.resources_cmd.boto3.client")
def test_json_output_structure(mock_boto, capsys):
    resources = [_make_resource()]
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator_response(resources)
    mock_boto.return_value = client

    result = cmd_resources(_args(output_json=True))
    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["LogicalId"] == "MyBucket"
    assert data[0]["Type"] == "AWS::S3::Bucket"


@patch("stackwatch.commands.resources_cmd.boto3.client")
def test_filter_type_reduces_results(mock_boto, capsys):
    resources = [
        _make_resource("MyBucket", "b", "AWS::S3::Bucket", "CREATE_COMPLETE"),
        _make_resource("MyQueue", "q", "AWS::SQS::Queue", "CREATE_COMPLETE"),
    ]
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator_response(resources)
    mock_boto.return_value = client

    result = cmd_resources(_args(filter_type="S3"))
    assert result == 0
    out = capsys.readouterr().out
    assert "MyBucket" in out
    assert "MyQueue" not in out


@patch("stackwatch.commands.resources_cmd.boto3.client")
def test_no_resources_after_filter(mock_boto, capsys):
    resources = [_make_resource()]
    client = MagicMock()
    client.get_paginator.return_value = _make_paginator_response(resources)
    mock_boto.return_value = client

    result = cmd_resources(_args(filter_type="Lambda"))
    assert result == 0
    assert "No resources found" in capsys.readouterr().out
