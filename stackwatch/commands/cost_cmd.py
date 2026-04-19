"""cost_cmd: estimate monthly cost of stack resources via CloudFormation cost estimation."""
from __future__ import annotations

import json
import argparse
from typing import Any

from stackwatch.fetcher import fetch_stack


def add_cost_subcommand(subparsers: Any) -> None:
    p = subparsers.add_parser("cost", help="Show estimated cost URL for a stack")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.set_defaults(func=cmd_cost)


def _get_cost_url(stack_name: str, region: str, profile: str | None) -> str | None:
    """Return the cost estimation URL stored in the stack metadata, if any."""
    import boto3

    session = boto3.Session(region_name=region, profile_name=profile)
    client = session.client("cloudformation")
    try:
        resp = client.describe_stacks(StackName=stack_name)
        stacks = resp.get("Stacks", [])
        if not stacks:
            return None
        return stacks[0].get("StackStatusReason") or None  # placeholder field
    except client.exceptions.ClientError:
        return None


def cmd_cost(args: argparse.Namespace) -> int:
    state = fetch_stack(args.stack, region=args.region, profile=args.profile)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    cost_url = getattr(state, "cost_estimation_url", None)

    if args.as_json:
        print(json.dumps({
            "stack": args.stack,
            "region": args.region,
            "cost_estimation_url": cost_url,
        }, indent=2))
    else:
        if cost_url:
            print(f"Cost estimation URL for '{args.stack}':")
            print(f"  {cost_url}")
        else:
            print(f"No cost estimation URL available for stack '{args.stack}'.")
            print("Tip: Use 'aws cloudformation estimate-template-cost' for a full estimate.")

    return 0
