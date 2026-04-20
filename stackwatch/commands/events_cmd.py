import json
from argparse import ArgumentParser, Namespace
from typing import List, Optional

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import format_no_data


def add_events_subcommand(subparsers) -> None:
    p: ArgumentParser = subparsers.add_parser(
        "events", help="Show recent CloudFormation stack events"
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--limit", type=int, default=20, help="Max number of events to show (default: 20)"
    )
    p.add_argument(
        "--json", dest="as_json", action="store_true", help="Output as JSON"
    )
    p.add_argument(
        "--filter-status",
        dest="filter_status",
        default=None,
        help="Only show events matching this status substring (e.g. FAILED)",
    )
    p.set_defaults(func=cmd_events)


def _fetch_events(stack_name: str, region: Optional[str], profile: Optional[str], limit: int) -> List[dict]:
    session = boto3.Session(region_name=region, profile_name=profile)
    cf = session.client("cloudformation")
    paginator = cf.get_paginator("describe_stack_events")
    events = []
    for page in paginator.paginate(StackName=stack_name):
        for event in page["StackEvents"]:
            events.append(event)
            if len(events) >= limit:
                return events
    return events


def cmd_events(args: Namespace) -> int:
    state = fetch_stack(args.stack, region=args.region, profile=args.profile)
    if state is None:
        print(format_no_data(args.stack))
        return 1

    try:
        events = _fetch_events(args.stack, args.region, args.profile, args.limit)
    except Exception as exc:  # pragma: no cover
        print(f"Error fetching events: {exc}")
        return 1

    if args.filter_status:
        needle = args.filter_status.upper()
        events = [e for e in events if needle in e.get("ResourceStatus", "")]

    if not events:
        print("No events found.")
        return 0

    if args.as_json:
        serialisable = [
            {
                "timestamp": e["Timestamp"].isoformat(),
                "logical_id": e.get("LogicalResourceId", ""),
                "status": e.get("ResourceStatus", ""),
                "reason": e.get("ResourceStatusReason", ""),
            }
            for e in events
        ]
        print(json.dumps(serialisable, indent=2))
    else:
        for e in events:
            ts = e["Timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            logical = e.get("LogicalResourceId", "-")
            status = e.get("ResourceStatus", "-")
            reason = e.get("ResourceStatusReason", "")
            line = f"[{ts}] {logical:40s} {status}"
            if reason:
                line += f"  — {reason}"
            print(line)

    return 0
