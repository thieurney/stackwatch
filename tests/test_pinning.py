"""Tests for stackwatch.pinning and stackwatch.commands.pinning_cmd."""
from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from stackwatch.pinning import (
    PinRegistry,
    PinnedStack,
    format_registry_plain,
    load_registry,
    save_registry,
)
from stackwatch.commands.pinning_cmd import (
    cmd_pin_add,
    cmd_pin_check,
    cmd_pin_list,
    cmd_pin_remove,
)


def _entry(name="MyStack", region="us-east-1", reason=None, pinned_at=None):
    return PinnedStack(stack_name=name, region=region, reason=reason, pinned_at=pinned_at)


def _args(pin_file, **kwargs):
    ns = types.SimpleNamespace(pin_file=str(pin_file), **kwargs)
    return ns


# --- PinRegistry unit tests ---

def test_is_pinned_false_when_empty():
    r = PinRegistry()
    assert not r.is_pinned("X", "us-east-1")


def test_add_and_is_pinned():
    r = PinRegistry()
    r.add(_entry())
    assert r.is_pinned("MyStack", "us-east-1")


def test_add_duplicate_is_idempotent():
    r = PinRegistry()
    r.add(_entry())
    r.add(_entry())
    assert len(r.entries) == 1


def test_remove_returns_true_and_removes():
    r = PinRegistry(entries=[_entry()])
    assert r.remove("MyStack", "us-east-1") is True
    assert not r.is_pinned("MyStack", "us-east-1")


def test_remove_missing_returns_false():
    r = PinRegistry()
    assert r.remove("Ghost", "eu-west-1") is False


def test_get_returns_entry():
    e = _entry(reason="do not touch")
    r = PinRegistry(entries=[e])
    assert r.get("MyStack", "us-east-1") is e


def test_get_returns_none_when_missing():
    assert PinRegistry().get("X", "us-east-1") is None


# --- save/load roundtrip ---

def test_save_and_load_roundtrip(tmp_path):
    pin_file = tmp_path / "pinned.json"
    r = PinRegistry(entries=[_entry(reason="locked", pinned_at="2024-01-01T00:00:00+00:00")])
    save_registry(r, str(pin_file))
    loaded = load_registry(str(pin_file))
    assert len(loaded.entries) == 1
    assert loaded.entries[0].reason == "locked"


def test_load_missing_returns_empty(tmp_path):
    r = load_registry(str(tmp_path / "nonexistent.json"))
    assert r.entries == []


# --- format ---

def test_format_empty():
    assert format_registry_plain(PinRegistry()) == "No stacks pinned."


def test_format_with_entry():
    r = PinRegistry(entries=[_entry(reason="critical")])
    out = format_registry_plain(r)
    assert "MyStack" in out
    assert "us-east-1" in out
    assert "critical" in out


# --- cmd_pin_add ---

def test_cmd_pin_add_creates_entry(tmp_path):
    pin_file = tmp_path / "p.json"
    args = _args(pin_file, stack_name="Alpha", region="eu-west-1", reason="test")
    out = []
    rc = cmd_pin_add(args, print_fn=out.append)
    assert rc == 0
    assert "Pinned" in out[0]
    r = load_registry(str(pin_file))
    assert r.is_pinned("Alpha", "eu-west-1")


def test_cmd_pin_add_already_pinned(tmp_path):
    pin_file = tmp_path / "p.json"
    r = PinRegistry(entries=[_entry()])
    save_registry(r, str(pin_file))
    args = _args(pin_file, stack_name="MyStack", region="us-east-1", reason=None)
    out = []
    rc = cmd_pin_add(args, print_fn=out.append)
    assert rc == 0
    assert "already pinned" in out[0]


# --- cmd_pin_remove ---

def test_cmd_pin_remove_success(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(entries=[_entry()]), str(pin_file))
    args = _args(pin_file, stack_name="MyStack", region="us-east-1")
    out = []
    rc = cmd_pin_remove(args, print_fn=out.append)
    assert rc == 0
    assert "Unpinned" in out[0]


def test_cmd_pin_remove_not_found(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(), str(pin_file))
    args = _args(pin_file, stack_name="Ghost", region="us-east-1")
    rc = cmd_pin_remove(args, print_fn=lambda _: None)
    assert rc == 1


# --- cmd_pin_list ---

def test_cmd_pin_list_plain(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(entries=[_entry()]), str(pin_file))
    args = _args(pin_file, as_json=False)
    out = []
    rc = cmd_pin_list(args, print_fn=out.append)
    assert rc == 0
    assert "MyStack" in out[0]


def test_cmd_pin_list_json(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(entries=[_entry(reason="x")]), str(pin_file))
    args = _args(pin_file, as_json=True)
    out = []
    cmd_pin_list(args, print_fn=out.append)
    data = json.loads(out[0])
    assert data[0]["stack_name"] == "MyStack"


# --- cmd_pin_check ---

def test_cmd_pin_check_pinned(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(entries=[_entry(reason="do not touch")]), str(pin_file))
    args = _args(pin_file, stack_name="MyStack", region="us-east-1")
    out = []
    rc = cmd_pin_check(args, print_fn=out.append)
    assert rc == 0
    assert "PINNED" in out[0]
    assert "do not touch" in out[0]


def test_cmd_pin_check_not_pinned(tmp_path):
    pin_file = tmp_path / "p.json"
    save_registry(PinRegistry(), str(pin_file))
    args = _args(pin_file, stack_name="Unknown", region="us-east-1")
    out = []
    rc = cmd_pin_check(args, print_fn=out.append)
    assert rc == 1
    assert "NOT PINNED" in out[0]
