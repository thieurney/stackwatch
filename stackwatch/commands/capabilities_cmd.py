from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

import boto3

from stackwatch.fetcher import fetch_stack


_CAPABILITY_DESCRIPTIONS = {
    "CAPABILITY_IAM": "Allows creation of IAM resources (roles, policies, users).",
    "CAPABILITY_NAMED_IAM": "Allows creation of named IAM resources.",
    "CAPABILITY_AUTO_EXPAND": "Allows use of macros and nested stacks with transforms.",
}


@dataclass
class CapabilityInfo:
    name: str
    description: str


def _fetch_capabilities(stack_name: str, session: boto3.Session) -> List[CapabilityInfo]:
    cf = session.client("cloudformation")
    resp = cf.describe_stacks(StackName=stack_name)
    stacks = resp.get("Stacks", [])
    if not stacks:
        return []
    raw: List[str] = stacks[0].get("Capabilities", [])
    return [
        CapabilityInfo(
            name=cap,
            description=_CAPABILITY_DESCRIPTIONS.get(cap, "No description available."),
        )
        for cap in raw
    ]


def _format_capabilities(caps: List[CapabilityInfo], use_json: bool) -> str:
    if use_json:
        return json.dumps([{"capability": c.name, "description": c.description} for c in caps], indent=2)
    if not caps:
        return "  (none)"
    lines = []
    for c in caps:
        lines.append(f"  {c.name}")
        lines.append(f"    {c.description}")
    return "\n".join(lines)


def add_capabilities_subcommand(subparsers) -> None:
    p = subparsers.add_parser("capabilities", help="Show IAM/transform capabilities declared for a stack")
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="use_json", action="store_true", default=False)
    p.set_defaults(func=cmd_capabilities)


def cmd_capabilities(args, session: Optional[boto3.Session] = None) -> int:
    if session is None:
        session = boto3.Session(region_name=args.region, profile_name=args.profile)

    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    caps = _fetch_capabilities(args.stack, session)
    print(f"Capabilities for {args.stack}:")
    print(_format_capabilities(caps, getattr(args, "use_json", False)))
    return 0
