from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.commands.dependencies_cmd import (
    StackDependency,
    _fetch_dependencies,
    cmd_dependencies,
)


def _args(**kwargs):
    defaults = dict(stack="my-stack", region=None, profile=None, as_json=False)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_paginator(pages: list[dict]):
    pag = MagicMock()
    pag.paginate.return_value = iter(pages)
    return pag


def _make_session(resource_pages=None, export_pages=None, import_pages=None):
    cf = MagicMock()
    cf.exceptions.ValidationError = Exception
    cf.exceptions.CFNRegistryException = Exception

    resource_pages = resource_pages or [{"StackResourceSummaries": []}]
    export_pages = export_pages or [{"Exports": []}]

    def get_paginator(name):
        if name == "list_stack_resources":
            return _make_paginator(resource_pages)
        if name == "list_exports":
            return _make_paginator(export_pages)
        if name == "list_imports":
            return _make_paginator(import_pages or [{"Imports": []}])
        raise ValueError(f"Unknown paginator: {name}")

    cf.get_paginator.side_effect = get_paginator
    session = MagicMock()
    session.client.return_value = cf
    return session


def test_fetch_returns_empty_when_no_deps():
    session = _make_session()
    result = _fetch_dependencies(session, "my-stack")
    assert result == []


def test_fetch_detects_nested_stack():
    resource_pages = [{
        "StackResourceSummaries": [{
            "ResourceType": "AWS::CloudFormation::Stack",
            "PhysicalResourceId": "arn:aws:cloudformation:us-east-1:123456789012:stack/child-stack/abc",
            "ResourceStatus": "CREATE_COMPLETE",
        }]
    }]
    session = _make_session(resource_pages=resource_pages)
    result = _fetch_dependencies(session, "my-stack")
    assert len(result) == 1
    assert result[0].stack_name == "child-stack"
    assert result[0].nested is True
    assert result[0].status == "CREATE_COMPLETE"


def test_fetch_detects_import_dependency():
    export_pages = [{
        "Exports": [{
            "Name": "MyVpcId",
            "ExportingStackId": "arn:aws:cloudformation:us-east-1:123:stack/my-stack/xyz",
        }]
    }]
    import_pages = [{"Imports": ["consumer-stack"]}]
    session = _make_session(export_pages=export_pages, import_pages=import_pages)
    result = _fetch_dependencies(session, "my-stack")
    assert any(d.stack_name == "consumer-stack" and not d.nested for d in result)


def test_cmd_prints_no_deps_message(capsys):
    session = _make_session()
    with patch("stackwatch.commands.dependencies_cmd.boto3.Session", return_value=session):
        rc = cmd_dependencies(_args())
    assert rc == 0
    captured = capsys.readouterr()
    assert "No dependencies" in captured.out


def test_cmd_json_output(capsys):
    resource_pages = [{
        "StackResourceSummaries": [{
            "ResourceType": "AWS::CloudFormation::Stack",
            "PhysicalResourceId": "arn:aws:cloudformation:us-east-1:123:stack/child/abc",
            "ResourceStatus": "UPDATE_COMPLETE",
        }]
    }]
    session = _make_session(resource_pages=resource_pages)
    with patch("stackwatch.commands.dependencies_cmd.boto3.Session", return_value=session):
        rc = cmd_dependencies(_args(as_json=True))
    assert rc == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["nested"] is True


def test_cmd_plain_output(capsys):
    resource_pages = [{
        "StackResourceSummaries": [{
            "ResourceType": "AWS::CloudFormation::Stack",
            "PhysicalResourceId": "arn:aws:cloudformation:us-east-1:123:stack/child/abc",
            "ResourceStatus": "CREATE_COMPLETE",
        }]
    }]
    session = _make_session(resource_pages=resource_pages)
    with patch("stackwatch.commands.dependencies_cmd.boto3.Session", return_value=session):
        rc = cmd_dependencies(_args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "child" in out
    assert "nested" in out
