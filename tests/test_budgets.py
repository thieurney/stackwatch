"""Tests for stackwatch.budgets."""
from stackwatch.budgets import (
    BudgetAlert,
    BudgetReport,
    _parse_alert,
    build_budget_report,
    format_budget_report,
)


def _raw(name="MyBudget", limit="100", actual="80", forecasted=None):
    raw = {
        "BudgetName": name,
        "BudgetLimit": {"Amount": limit, "Unit": "USD"},
        "CalculatedSpend": {
            "ActualSpend": {"Amount": actual, "Unit": "USD"},
        },
    }
    if forecasted is not None:
        raw["CalculatedSpend"]["ForecastedSpend"] = {"Amount": forecasted, "Unit": "USD"}
    return raw


def test_parse_alert_basic():
    alert = _parse_alert(_raw(actual="80"))
    assert alert.name == "MyBudget"
    assert alert.actual_spend == 80.0
    assert alert.limit_amount == 100.0
    assert alert.exceeded is False
    assert alert.pct_used == 80.0


def test_parse_alert_exceeded():
    alert = _parse_alert(_raw(actual="120"))
    assert alert.exceeded is True
    assert alert.pct_used == 120.0


def test_parse_alert_with_forecast():
    alert = _parse_alert(_raw(actual="50", forecasted="95"))
    assert alert.forecasted_spend == 95.0


def test_parse_alert_no_forecast():
    alert = _parse_alert(_raw(actual="50"))
    assert alert.forecasted_spend is None


def test_parse_alert_zero_limit_pct_is_none():
    alert = _parse_alert(_raw(limit="0", actual="10"))
    assert alert.pct_used is None


def test_build_budget_report_empty():
    report = build_budget_report("my-stack", [])
    assert report.stack_name == "my-stack"
    assert report.alerts == []
    assert report.has_exceeded is False
    assert report.exceeded_count == 0


def test_build_budget_report_multiple():
    report = build_budget_report("my-stack", [_raw(actual="80"), _raw(name="B2", actual="110")])
    assert len(report.alerts) == 2
    assert report.has_exceeded is True
    assert report.exceeded_count == 1


def test_format_no_alerts():
    report = BudgetReport(stack_name="my-stack", alerts=[])
    out = format_budget_report(report)
    assert "No budget data" in out


def test_format_ok_alert():
    report = build_budget_report("my-stack", [_raw(actual="50")])
    out = format_budget_report(report)
    assert "OK" in out
    assert "50.00/100.00" in out
    assert "50.0%" in out


def test_format_exceeded_alert():
    report = build_budget_report("my-stack", [_raw(actual="150")])
    out = format_budget_report(report)
    assert "EXCEEDED" in out


def test_format_with_color_exceeded():
    report = build_budget_report("my-stack", [_raw(actual="150")])
    out = format_budget_report(report, color=True)
    assert "\033[31m" in out


def test_format_with_color_ok():
    report = build_budget_report("my-stack", [_raw(actual="50")])
    out = format_budget_report(report, color=True)
    assert "\033[32m" in out


def test_format_includes_forecast():
    report = build_budget_report("my-stack", [_raw(actual="50", forecasted="95")])
    out = format_budget_report(report)
    assert "forecast 95.00" in out
