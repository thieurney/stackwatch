"""Tests for stackwatch.commands.permissions_cmd."""
import argparse
import pytest
from unittest.mock import MagicMock, patch

from stackwatch.fetcher import StackState
from stackwatch.commands.permissions_cmd import cmd_permissions, _fetch_resource_types


def _make_state(**kwargs) -> StackState:
    defaults = dict(
        name="my-stack",
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs={},
        capabilities=["CAPABILITY_IAM"],
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(stack="my-stack", env=None, region=None, as_json=False, no_color=True)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_paginator_response(types):
    page = {"StackResourceSummaries": [{"ResourceType": t, "LogicalResourceId": t} for t in types]}
    pag = MagicMock()
    pag.paginate.return_value = [page]
    return pag


def _run(state, resource_types, **arg_kwargs):
    args = _args(**arg_kwargs)
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = _make_paginator_response(resource_types)
    mock_session.client.return_value = mock_client

    with patch("stackwatch.commands.permissions_cmd.boto3.Session", return_value=mock_session), \
         patch("stackwatch.commands.permissions_cmd.fetch_stack", return_value=state):
        return cmd_permissions(args)


def test_returns_1_when_stack_not_found():
    assert _run(None, []) == 1


def test_returns_0_when_stack_found():
    state = _make_state()
    assert _run(state, ["AWS::S3::Bucket"]) == 0


def test_json_output_contains_stack_name(capsys):
    state = _make_state()
    _run(state, ["AWS::IAM::Role"], as_json=True)
    captured = capsys.readouterr()
    import json
    data = json.loads(captured.out)
    assert data["stack"] == "my-stack"


def test_warning_printed_when_iam_resource_no_capability(capsys):
    state = _make_state(capabilities=[])
    _run(state, ["AWS::IAM::Role"])
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_fetch_resource_types_deduplicates():
    client = MagicMock()
    page = {
        "StackResourceSummaries": [
            {"ResourceType": "AWS::S3::Bucket"},
            {"ResourceType": "AWS::S3::Bucket"},
            {"ResourceType": "AWS::IAM::Role"},
        ]
    }
    pag = MagicMock()
    pag.paginate.return_value = [page]
    client.get_paginator.return_value = pag
    result = _fetch_resource_types(client, "my-stack")
    assert result.count("AWS::S3::Bucket") == 1
    assert len(result) == 2
