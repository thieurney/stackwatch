"""Ownership tracking: extract and report stack owner metadata from tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from stackwatch.fetcher import StackState

_OWNER_TAG_KEYS = ("Owner", "owner", "Team", "team", "Contact", "contact")
_COST_CENTER_KEYS = ("CostCenter", "cost-center", "cost_center")


@dataclass
class OwnershipInfo:
    stack_name: str
    owner: Optional[str]
    team: Optional[str]
    cost_center: Optional[str]
    raw_tags: dict[str, str] = field(default_factory=dict)

    @property
    def has_owner(self) -> bool:
        return self.owner is not None

    @property
    def is_complete(self) -> bool:
        return all([self.owner, self.team, self.cost_center])


def _first_tag(tags: dict[str, str], *keys: str) -> Optional[str]:
    for k in keys:
        if k in tags:
            return tags[k]
    return None


def build_ownership_info(state: StackState) -> OwnershipInfo:
    tags = state.tags or {}
    owner = _first_tag(tags, "Owner", "owner")
    team = _first_tag(tags, "Team", "team")
    cost_center = _first_tag(tags, *_COST_CENTER_KEYS)
    return OwnershipInfo(
        stack_name=state.name,
        owner=owner,
        team=team,
        cost_center=cost_center,
        raw_tags=tags,
    )


def format_ownership_info(info: OwnershipInfo, *, use_color: bool = True) -> str:
    GREEN = "\033[32m" if use_color else ""
    YELLOW = "\033[33m" if use_color else ""
    RESET = "\033[0m" if use_color else ""

    def _val(v: Optional[str]) -> str:
        if v:
            return f"{GREEN}{v}{RESET}"
        return f"{YELLOW}(unset){RESET}"

    lines = [
        f"Stack   : {info.stack_name}",
        f"Owner   : {_val(info.owner)}",
        f"Team    : {_val(info.team)}",
        f"Cost Ctr: {_val(info.cost_center)}",
    ]
    return "\n".join(lines)
