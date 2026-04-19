import json
from argparse import Namespace
from io import StringIO
from unittest.mock import patch, MagicMock

from stackwatch.commands.drift_cmd import cmd_drift, _format_drift_status


def _make_state(drift_status="IN_SYNC", drifted_resources=None):
    state = MagicMock()
    state.drift_status = drift_status
    state.drifted_resources = drifted_resources or []
    return state


def _args(**kwargs):
    defaults = dict(stack="my-stack", region=None, profile=None, as_json=False, no_color=True)
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_returns_1_when_stack_not_found():
    out, err = StringIO(), StringIO()
    with patch("stackwatch.commands.drift_cmd.fetch_stack", return_value=None):
        rc = cmd_drift(_args(), out=out, err=err)
    assert rc == 1


def test_returns_0_on_in_sync():
    out, err = StringIO(), StringIO()
    with patch("stackwatch.commands.drift_cmd.fetch_stack", return_value=_make_state()):
        rc = cmd_drift(_args(), out=out, err=err)
    assert rc == 0
    assert "IN_SYNC" in out.getvalue()


def test_json_output():
    out, err = StringIO(), StringIO()
    state = _make_state(drift_status="DRIFTED", drifted_resources=["AWS::S3::Bucket/MyBucket"])
    with patch("stackwatch.commands.drift_cmd.fetch_stack", return_value=state):
        rc = cmd_drift(_args(as_json=True), out=out, err=err)
    assert rc == 0
    data = json.loads(out.getvalue())
    assert data["drift_status"] == "DRIFTED"
    assert "AWS::S3::Bucket/MyBucket" in data["drifted_resources"]


def test_drifted_resources_listed():
    out, err = StringIO(), StringIO()
    resources = ["AWS::EC2::Instance/Web", "AWS::RDS::DBInstance/DB"]
    state = _make_state(drift_status="DRIFTED", drifted_resources=resources)
    with patch("stackwatch.commands.drift_cmd.fetch_stack", return_value=state):
        rc = cmd_drift(_args(), out=out, err=err)
    assert rc == 0
    output = out.getvalue()
    assert "AWS::EC2::Instance/Web" in output
    assert "AWS::RDS::DBInstance/DB" in output


def test_format_drift_status_no_color():
    assert _format_drift_status("DRIFTED", no_color=True) == "DRIFTED"
    assert _format_drift_status(None, no_color=True) == "UNKNOWN"


def test_format_drift_status_with_color():
    result = _format_drift_status("DRIFTED", no_color=False)
    assert "DRIFTED" in result
    assert "\033[" in result


def test_format_drift_status_in_sync_color():
    result = _format_drift_status("IN_SYNC", no_color=False)
    assert "IN_SYNC" in result
    assert "\033[32m" in result
