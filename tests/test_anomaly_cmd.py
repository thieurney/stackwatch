"""Tests for stackwatch.commands.anomaly_cmd."""
import json
import argparse
from unittest.mock import MagicMock, patch

import pytest

from stackwatch.fetcher import StackState
from stackwatch.commands.anomaly_cmd import cmd_anomaly, _report_to_dict
from stackwatch.anomaly import build_anomaly_report


def _make_state(**kwargs) -> StackState:
    defaults = dict(
        stack_name="test-stack",
        status="CREATE_COMPLETE",
        parameters={"Env": "prod"},
        outputs={},
        tags={"Owner": "team"},
    )
    defaults.update(kwargs)
    return StackState(**defaults)


def _args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        stack="test-stack",
        profile=None,
        region=None,
        json_output=False,
        no_color=True,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _run(state, **kw):
    session = MagicMock()
    with patch("stackwatch.commands.anomaly_cmd.fetch_stack", return_value=state):
        return cmd_anomaly(_args(**kw), session)


def test_returns_1_when_stack_not_found(capsys):
    session = MagicMock()
    with patch("stackwatch.commands.anomaly_cmd.fetch_stack", return_value=None):
        rc = cmd_anomaly(_args(), session)
    assert rc == 1
    out = capsys.readouterr().out
    assert "not found" in out


def test_returns_0_for_healthy_stack(capsys):
    state = _make_state()
    rc = _run(state)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No anomalies" in out


def test_returns_1_for_high_severity(capsys):
    state = _make_state(status="ROLLBACK_COMPLETE")
    rc = _run(state)
    assert rc == 1
    out = capsys.readouterr().out
    assert "TERMINAL_STATUS" in out


def test_json_output_structure(capsys):
    state = _make_state(status="DELETE_FAILED", tags={})
    rc = _run(state, json_output=True)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["stack_name"] == "test-stack"
    assert data["has_anomalies"] is True
    assert isinstance(data["findings"], list)
    codes = {f["code"] for f in data["findings"]}
    assert "TERMINAL_STATUS" in codes


def test_report_to_dict_no_findings():
    state = _make_state()
    report = build_anomaly_report(state)
    d = _report_to_dict(report)
    assert d["has_anomalies"] is False
    assert d["findings"] == []
    assert d["high_count"] == 0


def test_json_output_returns_0_for_clean_stack(capsys):
    state = _make_state()
    rc = _run(state, json_output=True)
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["has_anomalies"] is False
