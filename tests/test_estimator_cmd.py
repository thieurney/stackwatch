"""Tests for stackwatch.commands.estimator_cmd."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from stackwatch.commands.estimator_cmd import (
    EstimatorResult,
    _fetch_estimator_url,
    cmd_estimator,
)


def _args(**kwargs):
    defaults = dict(
        stack="my-stack",
        region="us-east-1",
        profile=None,
        json_output=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _client_error(code="ValidationError"):
    return ClientError({"Error": {"Code": code, "Message": "err"}}, "op")


def _make_session(stack_exists=True, template_body="{}", estimator_url="https://calc.example.com"):
    session = MagicMock()
    session.region_name = "us-east-1"
    client = MagicMock()
    session.client.return_value = client

    if not stack_exists:
        client.describe_stacks.side_effect = _client_error()
    else:
        client.describe_stacks.return_value = {}

    client.get_template.return_value = {"TemplateBody": template_body}
    client.estimate_template_cost.return_value = {"Url": estimator_url}
    return session, client


class TestFetchEstimatorUrl:
    def test_returns_url_on_success(self):
        _, client = _make_session()
        url = _fetch_estimator_url(client, "my-stack")
        assert url == "https://calc.example.com"

    def test_returns_none_when_template_empty(self):
        _, client = _make_session(template_body="")
        url = _fetch_estimator_url(client, "my-stack")
        assert url is None

    def test_returns_none_on_client_error(self):
        _, client = _make_session()
        client.get_template.side_effect = _client_error()
        url = _fetch_estimator_url(client, "my-stack")
        assert url is None


class TestCmdEstimator:
    def test_returns_1_when_stack_not_found(self, capsys):
        session, _ = _make_session(stack_exists=False)
        rc = cmd_estimator(_args(), session=session)
        assert rc == 1
        out = capsys.readouterr().out
        assert "not found" in out

    def test_returns_0_when_url_found(self, capsys):
        session, _ = _make_session(estimator_url="https://calc.example.com")
        rc = cmd_estimator(_args(), session=session)
        assert rc == 0
        out = capsys.readouterr().out
        assert "https://calc.example.com" in out

    def test_json_output_structure(self, capsys):
        session, _ = _make_session(estimator_url="https://calc.example.com")
        rc = cmd_estimator(_args(json_output=True), session=session)
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert data["stack"] == "my-stack"
        assert data["estimator_url"] == "https://calc.example.com"
        assert "region" in data

    def test_no_url_prints_tip(self, capsys):
        session, client = _make_session()
        client.estimate_template_cost.return_value = {}
        rc = cmd_estimator(_args(), session=session)
        assert rc == 0
        out = capsys.readouterr().out
        assert "No estimator URL" in out
        assert "Tip" in out
