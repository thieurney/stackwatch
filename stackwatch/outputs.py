"""Utilities for working with CloudFormation stack outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stackwatch.fetcher import StackState


@dataclass
class StackOutput:
    key: str
    value: str
    description: Optional[str] = None
    export_name: Optional[str] = None


@dataclass
class OutputDiff:
    key: str
    old_value: Optional[str]
    new_value: Optional[str]


def parse_outputs(state: StackState) -> List[StackOutput]:
    """Extract structured outputs from a StackState."""
    raw: List[Dict] = state.raw.get("Outputs", [])
    result = []
    for item in raw:
        result.append(
            StackOutput(
                key=item.get("OutputKey", ""),
                value=item.get("OutputValue", ""),
                description=item.get("Description"),
                export_name=item.get("ExportName"),
            )
        )
    return result


def outputs_as_dict(state: StackState) -> Dict[str, str]:
    """Return a {key: value} mapping of stack outputs."""
    return {o.key: o.value for o in parse_outputs(state)}


def diff_outputs(old: StackState, new: StackState) -> List[OutputDiff]:
    """Produce a list of OutputDiff for changed/added/removed outputs."""
    old_map = outputs_as_dict(old)
    new_map = outputs_as_dict(new)
    all_keys = set(old_map) | set(new_map)
    diffs = []
    for key in sorted(all_keys):
        ov = old_map.get(key)
        nv = new_map.get(key)
        if ov != nv:
            diffs.append(OutputDiff(key=key, old_value=ov, new_value=nv))
    return diffs


def has_output_changes(old: StackState, new: StackState) -> bool:
    return bool(diff_outputs(old, new))
