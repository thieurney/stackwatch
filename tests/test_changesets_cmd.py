import io
import json
import pytest
from unittest.mock import MagicMock, patch
from stackwatch.commands.changesets_cmd import (
    ChangeSetSummary,
    _fetch_changesets,
    cmd_changesets,
)


def _args(**kwargs):
    defaults = {"stack": "my-stack", "region": "us-east-1", "as_json": False}
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_changeset(name="cs-1", status="CREATE_COMPLETE", reason=None, description=None):
    return ChangeSetSummary(
        name=name,
        status=status,
        status_reason=reason,
        creation_time="2024-01-01 10:00:00",
        description=description,
    )


def _make_paginator_response(summaries):
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Summaries": summaries}]
    return paginator


def test_returns_1_when_stack_not_found():
    with patch("stackwatch.commands.changesets_cmd._fetch_changesets", return_value=[]):
        out = io.StringIO()
        result = cmd_changesets(_args(), out)
    assert result == 0
    assert "No change sets" in out.getvalue()


def test_returns_0_with_changesets():
    cs = _make_changeset()
    with patch("stackwatch.commands.changesets_cmd._fetch_changesets", return_value=[cs]):
        out = io.StringIO()
        result = cmd_changesets(_args(), out)
    assert result == 0
    assert "cs-1" in out.getvalue()
    assert "CREATE_COMPLETE" in out.getvalue()


def test_json_output_structure():
    cs = _make_changeset(name="cs-json", description="my desc")
    with patch("stackwatch.commands.changesets_cmd._fetch_changesets", return_value=[cs]):
        out = io.StringIO()
        result = cmd_changesets(_args(as_json=True), out)
    assert result == 0
    data = json.loads(out.getvalue())
    assert isinstance(data, list)
    assert data[0]["name"] == "cs-json"
    assert data[0]["description"] == "my desc"


def test_shows_reason_and_description():
    cs = _make_changeset(reason="some reason", description="some desc")
    with patch("stackwatch.commands.changesets_cmd._fetch_changesets", return_value=[cs]):
        out = io.StringIO()
        cmd_changesets(_args(), out)
    text = out.getvalue()
    assert "some reason" in text
    assert "some desc" in text


def test_fetch_changesets_calls_paginator():
    raw = [
        {
            "ChangeSetName": "cs-1",
            "Status": "CREATE_COMPLETE",
            "CreationTime": "2024-01-01",
        }
    ]
    mock_paginator = _make_paginator_response(raw)
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    with patch("boto3.client", return_value=mock_client):
        result = _fetch_changesets("my-stack", "us-east-1")
    assert len(result) == 1
    assert result[0].name == "cs-1"
