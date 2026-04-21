"""Command to display CloudFormation account/region limits and current usage."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

import boto3


@dataclass
class CfnLimit:
    name: str
    value: int
    used: Optional[int] = None

    @property
    def remaining(self) -> Optional[int]:
        if self.used is None:
            return None
        return self.value - self.used

    @property
    def pct_used(self) -> Optional[float]:
        if self.used is None or self.value == 0:
            return None
        return round(self.used / self.value * 100, 1)


def _fetch_limits(session: boto3.Session) -> List[CfnLimit]:
    client = session.client("cloudformation")
    resp = client.describe_account_limits()
    raw = resp.get("AccountLimits", [])
    return [
        CfnLimit(name=item["Name"], value=item["Value"])
        for item in raw
    ]


def _format_limits(limits: List[CfnLimit], use_json: bool) -> str:
    if use_json:
        data = [
            {
                "name": lim.name,
                "limit": lim.value,
                "used": lim.used,
                "remaining": lim.remaining,
                "pct_used": lim.pct_used,
            }
            for lim in limits
        ]
        return json.dumps(data, indent=2)

    lines = []
    header = f"{'Limit':<40} {'Max':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    for lim in limits:
        lines.append(f"{lim.name:<40} {lim.value:>10}")
    return "\n".join(lines)


def add_limits_subcommand(subparsers) -> None:
    p = subparsers.add_parser("limits", help="Show CloudFormation account limits")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="use_json", action="store_true", help="JSON output")
    p.set_defaults(func=cmd_limits)


def cmd_limits(args) -> int:
    session = boto3.Session(
        region_name=getattr(args, "region", None),
        profile_name=getattr(args, "profile", None),
    )
    limits = _fetch_limits(session)
    if not limits:
        print("No limit information returned.")
        return 0
    print(_format_limits(limits, use_json=getattr(args, "use_json", False)))
    return 0
