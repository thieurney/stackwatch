"""Tests for stackwatch.commands.budgets_cmd."""
from unittest.mock import MagicMock, patch
import json
import pytest

from stackwatch.commands.budgets_cmd import cmd_budgets, _fetch_raw_budgets
from stackwatch.fetcher import StackState


def _make_state(name="my-stack"):
    return StackState(
        name=name,
        status="UPDATE_COMPLETE",
        parameters={},
        tags={},
        outputs={},
        capabilities=[],
        termination_protection=True,
        last_updated=None,
        creation_time=None,
        description="",
        role_arn=None,
        notification_arns=[],
        raw={},
    )


def _args(**kwargs):
    base = dict(
        stack="my-stack",
        region=None,
        profile=None,
        account_id="123456789012",
        as_json=False,
        no_color=True,
    )
    base.update(kwargs)
    ns = MagicMock()
    for k, v in base.items():
        setattr(ns, k, v)
    return ns


def _raw_budget(name="my-stack-budget", actual="80", limit="100"):
    return {
        "BudgetName": name,
        "BudgetLimit": {"Amount": limit, "Unit": "USD"},
        "CalculatedSpend": {"ActualSpend": {"Amount": actual, "Unit": "USD"}},
    }


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.budgets_cmd.fetch_stack", return_value=None), \
         patch("stackwatch.commands.budgets_cmd.boto3.Session"):
        result = cmd_budgets(_args())
    assert result == 1


def test_returns_0_when_no_alerts():
    with patch("stackwatch.commands.budgets_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.budgets_cmd.boto3.Session"), \
         patch("stackwatch.commands.budgets_cmd._fetch_raw_budgets", return_value=[]):
        result = cmd_budgets(_args())
    assert result == 0


def test_returns_1_when_budget_exceeded(capsys):
    with patch("stackwatch.commands.budgets_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.budgets_cmd.boto3.Session"), \
         patch("stackwatch.commands.budgets_cmd._fetch_raw_budgets",
               return_value=[_raw_budget(actual="150")]):
        result = cmd_budgets(_args())
    assert result == 1
    out = capsys.readouterr().out
    assert "EXCEEDED" in out


def test_json_output_structure(capsys):
    with patch("stackwatch.commands.budgets_cmd.fetch_stack", return_value=_make_state()), \
         patch("stackwatch.commands.budgets_cmd.boto3.Session"), \
         patch("stackwatch.commands.budgets_cmd._fetch_raw_budgets",
               return_value=[_raw_budget(actual="80")]):
        result = cmd_budgets(_args(as_json=True))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["stack"] == "my-stack"
    assert "alerts" in data
    assert data["alerts"][0]["actual_spend"] == 80.0
    assert result == 0


def test_fetch_raw_budgets_filters_by_stack_name():
    session = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Budgets": [
            {"BudgetName": "my-stack-monthly"},
            {"BudgetName": "other-stack-monthly"},
        ]}
    ]
    session.client.return_value.get_paginator.return_value = paginator
    results = _fetch_raw_budgets(session, "123456789012", "my-stack")
    assert len(results) == 1
    assert results[0]["BudgetName"] == "my-stack-monthly"
