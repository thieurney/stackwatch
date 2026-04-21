"""CLI command: stackwatch permissions <stack> [--env ...] [--json]."""
from __future__ import annotations

import argparse
from typing import Optional

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.permissions import parse_permission_summary, format_permission_summary


def _fetch_resource_types(client, stack_name: str) -> list[str]:
    """Return a deduplicated list of resource types in the stack."""
    types: set[str] = set()
    paginator = client.get_paginator("list_stack_resources")
    for page in paginator.paginate(StackName=stack_name):
        for r in page.get("StackResourceSummaries", []):
            rt = r.get("ResourceType")
            if rt:
                types.add(rt)
    return sorted(types)


def add_permissions_subcommand(subparsers) -> None:
    p = subparsers.add_parser(
        "permissions",
        help="Show IAM capabilities and resource types for a stack.",
    )
    p.add_argument("stack", help="CloudFormation stack name or ARN.")
    p.add_argument("--env", default=None, help="AWS profile name.")
    p.add_argument("--region", default=None, help="AWS region.")
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON.")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI color.")
    p.set_defaults(func=cmd_permissions)


def cmd_permissions(args: argparse.Namespace) -> int:
    session = boto3.Session(
        profile_name=args.env,
        region_name=getattr(args, "region", None),
    )
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack not found: {args.stack}")
        return 1

    client = session.client("cloudformation")
    resource_types = _fetch_resource_types(client, args.stack)

    summary = parse_permission_summary(
        stack_name=args.stack,
        capabilities=state.capabilities,
        resource_types=resource_types,
    )

    use_color = not getattr(args, "no_color", False)
    print(format_permission_summary(summary, use_color=use_color, as_json=getattr(args, "as_json", False)))
    return 0
