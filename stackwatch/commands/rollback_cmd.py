"""Command to show rollback triggers configured on a CloudFormation stack."""
from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack


def add_rollback_subcommand(subparsers: Any) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        "rollback",
        help="Show rollback triggers for a CloudFormation stack.",
    )
    parser.add_argument("stack", help="Stack name or ARN")
    parser.add_argument("--profile", default=None, help="AWS profile name")
    parser.add_argument("--region", default=None, help="AWS region")
    parser.add_argument(
        "--json", dest="as_json", action="store_true", help="Output as JSON"
    )
    parser.set_defaults(func=cmd_rollback)


def _fetch_rollback_config(stack_name: str, session: Any) -> dict:
    """Return the RollbackConfiguration dict for the given stack."""
    cf = session.client("cloudformation")
    response = cf.describe_stacks(StackName=stack_name)
    stacks = response.get("Stacks", [])
    if not stacks:
        return {}
    return stacks[0].get("RollbackConfiguration", {})


def _format_rollback_config(config: dict) -> str:
    """Return a human-readable representation of rollback configuration."""
    triggers = config.get("RollbackTriggers", [])
    monitoring = config.get("MonitoringTimeInMinutes", 0)

    if not triggers:
        return "No rollback triggers configured."

    lines = [f"Monitoring window : {monitoring} minute(s)", "Triggers:"]
    for t in triggers:
        lines.append(f"  Arn  : {t.get('Arn', 'n/a')}")
        lines.append(f"  Type : {t.get('Type', 'n/a')}")
        lines.append("")
    return "\n".join(lines).rstrip()


def cmd_rollback(args: Namespace) -> int:
    session = boto3.Session(
        profile_name=args.profile, region_name=getattr(args, "region", None)
    )

    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    config = _fetch_rollback_config(args.stack, session)

    if args.as_json:
        print(json.dumps(config, indent=2, default=str))
    else:
        print(_format_rollback_config(config))

    return 0
