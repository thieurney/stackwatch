"""CLI command: stackwatch lineage — show stack age and update history."""
from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.lineage import build_lineage, format_lineage


def add_lineage_subcommand(subparsers: Any) -> None:
    p: ArgumentParser = subparsers.add_parser(
        "lineage",
        help="Show stack creation age and update history",
    )
    p.add_argument("stack", help="CloudFormation stack name")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    p.add_argument("--no-color", action="store_true", help="Disable color output")
    p.set_defaults(func=cmd_lineage)


def _fetch_raw_events(client: Any, stack_name: str) -> list:
    paginator = client.get_paginator("describe_stack_events")
    events = []
    for page in paginator.paginate(StackName=stack_name):
        events.extend(page.get("StackEvents", []))
    return events


def cmd_lineage(args: Namespace) -> int:
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    cf = session.client("cloudformation")

    state = fetch_stack(args.stack, cf)
    if state is None:
        print(f"Stack not found: {args.stack}")
        return 1

    raw_events = _fetch_raw_events(cf, args.stack)
    lineage = build_lineage(args.stack, raw_events)

    if args.json_output:
        data = {
            "stack_name": lineage.stack_name,
            "created_at": lineage.created_at.isoformat() if lineage.created_at else None,
            "last_updated_at": lineage.last_updated_at.isoformat() if lineage.last_updated_at else None,
            "age_days": round(lineage.age_days, 2) if lineage.age_days is not None else None,
            "update_count": lineage.update_count,
            "total_events": len(lineage.events),
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_lineage(lineage, use_color=not args.no_color))

    return 0
