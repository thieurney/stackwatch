"""Tests for stackwatch.commands.stacksets_cmd."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stackwatch.commands.stacksets_cmd import (
    StackSetInstance,
    _fetch_stackset_instances,
    _format_instances,
    cmd_stacksets,
)


def _make_instance(account="111111111111", region="us-east-1", status="CURRENT", reason=None, stack_id=None):
    return StackSetInstance(account=account, region=region, status=status, status_reason=reason, stack_id=stack_id)


def _args(stackset_name="MyStackSet", use_json=False):
    return SimpleNamespace(stackset_name=stackset_name, use_json=use_json)


def _make_session(pages):
    paginator = MagicMock()
    paginator.paginate.return_value = iter(pages)
    cf = MagicMock()
    cf.get_paginator.return_value = paginator
    session = MagicMock()
    session.client.return_value = cf
    return session


# --- _fetch_stackset_instances ---

def test_fetch_returns_empty_when_no_summaries():
    session = _make_session([{"Summaries": []}])
    result = _fetch_stackset_instances(session, "MyStackSet")
    assert result == []


def test_fetch_maps_fields_correctly():
    page = {
        "Summaries": [
            {"Account": "123", "Region": "eu-west-1", "Status": "OUTDATED", "StatusReason": "drift", "StackId": "arn:aws:..."},
        ]
    }
    session = _make_session([page])
    result = _fetch_stackset_instances(session, "MyStackSet")
    assert len(result) == 1
    inst = result[0]
    assert inst.account == "123"
    assert inst.region == "eu-west-1"
    assert inst.status == "OUTDATED"
    assert inst.status_reason == "drift"
    assert inst.stack_id == "arn:aws:..."


# --- _format_instances ---

def test_format_empty_list_plain():
    assert _format_instances([], use_json=False) == "  (no instances found)"


def test_format_plain_includes_account_region_status():
    inst = _make_instance()
    output = _format_instances([inst], use_json=False)
    assert "111111111111" in output
    assert "us-east-1" in output
    assert "CURRENT" in output


def test_format_plain_includes_reason_when_present():
    inst = _make_instance(reason="something went wrong")
    output = _format_instances([inst], use_json=False)
    assert "something went wrong" in output


def test_format_json_structure():
    inst = _make_instance(status="OUTDATED", reason="old")
    output = _format_instances([inst], use_json=True)
    data = json.loads(output)
    assert isinstance(data, list)
    assert data[0]["status"] == "OUTDATED"
    assert data[0]["status_reason"] == "old"


# --- cmd_stacksets ---

def test_returns_1_on_client_error():
    session = MagicMock()
    session.client.side_effect = Exception("no access")
    assert cmd_stacksets(_args(), session) == 1


def test_returns_0_with_no_instances(capsys):
    session = _make_session([{"Summaries": []}])
    rc = cmd_stacksets(_args(), session)
    assert rc == 0
    captured = capsys.readouterr()
    assert "No instances" in captured.out


def test_returns_0_with_instances(capsys):
    page = {"Summaries": [{"Account": "999", "Region": "ap-southeast-1", "Status": "CURRENT"}]}
    session = _make_session([page])
    rc = cmd_stacksets(_args(), session)
    assert rc == 0
    captured = capsys.readouterr()
    assert "MyStackSet" in captured.out
    assert "999" in captured.out
