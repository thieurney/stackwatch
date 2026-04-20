"""Command to fetch and display a CloudFormation stack's policy."""
from __future__ import annotations

import json
import argparse
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack


def add_policy_subcommand(subparsers: Any) -> None:
    p = subparsers.add_parser(
        "policy",
        help="Show the stack policy for a CloudFormation stack",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--json", dest="as_json", action="store_true",
        help="Output raw policy JSON",
    )
    p.set_defaults(func=cmd_policy)


def _fetch_policy(stack_name: str, region: str | None, profile: str | None) -> dict | None:
    """Return the stack policy document or None if no policy is set."""
    session = boto3.Session(region_name=region, profile_name=profile)
    client = session.client("cloudformation")
    resp = client.get_stack_policy(StackName=stack_name)
    body = resp.get("StackPolicyBody")
    if not body:
        return None
    return json.loads(body)


def _format_policy(policy: dict) -> str:
    lines = []
    statements = policy.get("Statement", [])
    for stmt in statements:
        effect = stmt.get("Effect", "?")
        principal = stmt.get("Principal", "*")
        action = stmt.get("Action", "*")
        resource = stmt.get("Resource", "*")
        condition = stmt.get("Condition")
        lines.append(
            f"  [{effect}] Principal={principal}  Action={action}  Resource={resource}"
        )
        if condition:
            lines.append(f"    Condition: {json.dumps(condition)}")
    return "\n".join(lines) if lines else "  (no statements)"


def cmd_policy(args: argparse.Namespace) -> int:
    state = fetch_stack(args.stack, region=args.region, profile=args.profile)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    try:
        policy = _fetch_policy(args.stack, region=args.region, profile=args.profile)
    except Exception as exc:  # pragma: no cover
        print(f"Error fetching policy: {exc}")
        return 1

    if policy is None:
        print(f"No stack policy is set for '{args.stack}'.")
        return 0

    if args.as_json:
        print(json.dumps(policy, indent=2))
    else:
        print(f"Stack policy for '{args.stack}':")
        print(_format_policy(policy))

    return 0
