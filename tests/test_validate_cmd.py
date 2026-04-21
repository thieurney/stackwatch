"""Unit tests for stackwatch.commands.validate_cmd."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest
from botocore.exceptions import ClientError

from stackwatch.commands.validate_cmd import cmd_validate


def _args(**kwargs):
    defaults = {
        "file": None,
        "url": None,
        "output_json": False,
        "profile": None,
        "region": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_session(response: dict):
    cf = MagicMock()
    cf.validate_template.return_value = response
    session = MagicMock()
    session.client.return_value = cf
    return session


def _client_error(message: str = "bad template"):
    return ClientError(
        {"Error": {"Code": "ValidationError", "Message": message}},
        "ValidateTemplate",
    )


_VALID_RESPONSE = {
    "Parameters": [{"ParameterKey": "Env", "DefaultValue": "prod"}],
    "Description": "Test stack",
    "Capabilities": ["CAPABILITY_IAM"],
    "CapabilitiesReason": "Has IAM",
}


@patch("stackwatch.commands.validate_cmd.boto3.Session")
@patch("builtins.open", mock_open(read_data="TemplateBody: {}"))
def test_returns_0_on_valid_file(mock_boto):
    mock_boto.return_value = _mock_session(_VALID_RESPONSE)
    rc = cmd_validate(_args(file="template.yaml"))
    assert rc == 0


@patch("stackwatch.commands.validate_cmd.boto3.Session")
def test_returns_0_on_valid_url(mock_boto):
    mock_boto.return_value = _mock_session(_VALID_RESPONSE)
    rc = cmd_validate(_args(url="https://s3.amazonaws.com/bucket/tpl.yaml"))
    assert rc == 0


@patch("stackwatch.commands.validate_cmd.boto3.Session")
def test_returns_1_on_client_error(mock_boto, capsys):
    session = MagicMock()
    session.client.return_value.validate_template.side_effect = _client_error("bad")
    mock_boto.return_value = session
    rc = cmd_validate(_args(url="s3://bucket/tpl"))
    assert rc == 1
    out = capsys.readouterr().out
    assert "bad" in out


def test_returns_1_when_file_not_found(capsys):
    with patch("stackwatch.commands.validate_cmd.boto3.Session"):
        rc = cmd_validate(_args(file="/nonexistent/template.yaml"))
    assert rc == 1


@patch("stackwatch.commands.validate_cmd.boto3.Session")
def test_json_output_structure(mock_boto, capsys):
    import json

    mock_boto.return_value = _mock_session(_VALID_RESPONSE)
    rc = cmd_validate(_args(url="s3://b/t", output_json=True))
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "capabilities" in data
    assert "parameters" in data
    assert data["parameters"][0]["key"] == "Env"
