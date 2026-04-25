"""Stack pinning: mark stacks as pinned to prevent accidental changes."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_DEFAULT_PIN_FILE = os.path.expanduser("~/.stackwatch/pinned.json")


@dataclass
class PinnedStack:
    stack_name: str
    region: str
    reason: Optional[str] = None
    pinned_at: Optional[str] = None


@dataclass
class PinRegistry:
    entries: List[PinnedStack] = field(default_factory=list)

    def is_pinned(self, stack_name: str, region: str) -> bool:
        return any(
            e.stack_name == stack_name and e.region == region
            for e in self.entries
        )

    def get(self, stack_name: str, region: str) -> Optional[PinnedStack]:
        for e in self.entries:
            if e.stack_name == stack_name and e.region == region:
                return e
        return None

    def add(self, entry: PinnedStack) -> None:
        if not self.is_pinned(entry.stack_name, entry.region):
            self.entries.append(entry)

    def remove(self, stack_name: str, region: str) -> bool:
        before = len(self.entries)
        self.entries = [
            e for e in self.entries
            if not (e.stack_name == stack_name and e.region == region)
        ]
        return len(self.entries) < before


def load_registry(path: str = _DEFAULT_PIN_FILE) -> PinRegistry:
    p = Path(path)
    if not p.exists():
        return PinRegistry()
    data = json.loads(p.read_text())
    entries = [PinnedStack(**e) for e in data.get("pinned", [])]
    return PinRegistry(entries=entries)


def save_registry(registry: PinRegistry, path: str = _DEFAULT_PIN_FILE) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pinned": [
        {"stack_name": e.stack_name, "region": e.region,
         "reason": e.reason, "pinned_at": e.pinned_at}
        for e in registry.entries
    ]}
    p.write_text(json.dumps(payload, indent=2))


def format_registry_plain(registry: PinRegistry) -> str:
    if not registry.entries:
        return "No stacks pinned."
    lines = []
    for e in registry.entries:
        reason_str = f"  reason: {e.reason}" if e.reason else ""
        pinned_str = f"  pinned_at: {e.pinned_at}" if e.pinned_at else ""
        lines.append(f"  {e.stack_name} ({e.region}){reason_str}{pinned_str}")
    return "Pinned stacks:\n" + "\n".join(lines)
