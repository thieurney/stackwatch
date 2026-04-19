"""Snapshot: save and load stack states to/from disk for later diffing."""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from stackwatch.fetcher import StackState

DEFAULT_SNAPSHOT_DIR = os.path.expanduser("~/.stackwatch/snapshots")


def _snapshot_path(stack_name: str, label: str, directory: str) -> str:
    safe_name = stack_name.replace("/", "_")
    safe_label = label.replace("/", "_")
    return os.path.join(directory, f"{safe_name}__{safe_label}.json")


def save_snapshot(
    state: StackState,
    label: str,
    directory: str = DEFAULT_SNAPSHOT_DIR,
) -> str:
    """Persist a StackState to disk. Returns the file path written."""
    os.makedirs(directory, exist_ok=True)
    path = _snapshot_path(state.stack_name, label, directory)
    payload = {
        "stack_name": state.stack_name,
        "status": state.status,
        "parameters": state.parameters,
        "outputs": state.outputs,
        "tags": state.tags,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def load_snapshot(
    stack_name: str,
    label: str,
    directory: str = DEFAULT_SNAPSHOT_DIR,
) -> Optional[StackState]:
    """Load a previously saved StackState. Returns None if not found."""
    path = _snapshot_path(stack_name, label, directory)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return StackState(
        stack_name=data["stack_name"],
        status=data["status"],
        parameters=data.get("parameters", {}),
        outputs=data.get("outputs", {}),
        tags=data.get("tags", {}),
    )


def list_snapshots(directory: str = DEFAULT_SNAPSHOT_DIR) -> list[dict]:
    """Return metadata for all snapshots found in the directory."""
    if not os.path.isdir(directory):
        return []
    results = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(directory, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            results.append({
                "stack_name": data.get("stack_name"),
                "label": data.get("label"),
                "status": data.get("status"),
                "saved_at": data.get("saved_at"),
                "path": fpath,
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return results
