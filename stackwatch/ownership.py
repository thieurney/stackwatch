"""Ownership tracking for CloudFormation stacks via tags and metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from stackwatch.fetcher import StackState

_OWNER_TAG_KEYS = ("Owner", "owner", "Team", "team", "Contact", "contact")
_TEAM_TAG_KEYS = ("Team", "team", "Squad", "squad")
_ENV_TAG_KEYS = ("Environment", "environment", "Env", "env")


@dataclass
class OwnershipInfo:
    stack_name: str
    owner: Optional[str] = None
    team: Optional[str] = None
    environment: Optional[str] = None
    extra_tags: dict[str, str] = field(default_factory=dict)

    @property
    def is_owned(self) -> bool:
        return self.owner is not None or self.team is not None


def _first_tag(tags: dict[str, str], keys: tuple[str, ...]) -> Optional[str]:
    for k in keys:
        if k in tags:
            return tags[k]
    return None


def build_ownership_info(state: StackState) -> OwnershipInfo:
    tags = state.tags or {}
    known_keys = set(_OWNER_TAG_KEYS) | set(_TEAM_TAG_KEYS) | set(_ENV_TAG_KEYS)
    extra = {k: v for k, v in tags.items() if k not in known_keys}
    return OwnershipInfo(
        stack_name=state.name,
        owner=_first_tag(tags, _OWNER_TAG_KEYS),
        team=_first_tag(tags, _TEAM_TAG_KEYS),
        environment=_first_tag(tags, _ENV_TAG_KEYS),
        extra_tags=extra,
    )


def format_ownership_plain(info: OwnershipInfo) -> str:
    lines = [f"Stack:       {info.stack_name}"]
    lines.append(f"Owner:       {info.owner or '(unset)'}")
    lines.append(f"Team:        {info.team or '(unset)'}")
    lines.append(f"Environment: {info.environment or '(unset)'}")
    if info.extra_tags:
        lines.append("Extra tags:")
        for k, v in sorted(info.extra_tags.items()):
            lines.append(f"  {k}: {v}")
    if not info.is_owned:
        lines.append("WARNING: no owner or team tag found")
    return "\n".join(lines)
