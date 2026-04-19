"""Diff two StackState objects and produce a structured report."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from stackwatch.fetcher import StackState


@dataclass
class FieldDiff:
    key: str
    left: str
    right: str


@dataclass
class StackDiff:
    stack_name: str
    left_env: str
    right_env: str
    status_diff: List[FieldDiff] = field(default_factory=list)
    parameter_diffs: List[FieldDiff] = field(default_factory=list)
    output_diffs: List[FieldDiff] = field(default_factory=list)
    tag_diffs: List[FieldDiff] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any([
            self.status_diff,
            self.parameter_diffs,
            self.output_diffs,
            self.tag_diffs,
        ])


def _diff_dicts(left: Dict[str, str], right: Dict[str, str]) -> List[FieldDiff]:
    diffs = []
    all_keys = set(left) | set(right)
    for key in sorted(all_keys):
        l_val = left.get(key, "<missing>")
        r_val = right.get(key, "<missing>")
        if l_val != r_val:
            diffs.append(FieldDiff(key=key, left=l_val, right=r_val))
    return diffs


def diff_stacks(left: StackState, right: StackState, left_env: str, right_env: str) -> StackDiff:
    """Compare two StackState objects and return a StackDiff."""
    result = StackDiff(stack_name=left.name, left_env=left_env, right_env=right_env)

    if left.status != right.status:
        result.status_diff.append(
            FieldDiff(key="status", left=left.status, right=right.status)
        )

    result.parameter_diffs = _diff_dicts(left.parameters, right.parameters)
    result.output_diffs = _diff_dicts(left.outputs, right.outputs)
    result.tag_diffs = _diff_dicts(left.tags, right.tags)

    return result
