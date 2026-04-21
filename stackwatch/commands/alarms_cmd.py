"""CLI sub-command: stackwatch alarms <stack> — show CloudWatch alarms for a stack."""
from __future__ import annotations

import argparse
from typing import Any

import boto3

from stackwatch.alarms import AlarmSummary, parse_alarm, format_alarm_summary
from stackwatch.fetcher import fetch_stack


def _fetch_alarms(session: Any, stack_name: str) -> AlarmSummary:
    """Discover alarms linked to stack resources via CloudFormation resource list."""
    cfn = session.client("cloudformation")
    cw = session.client("cloudwatch")

    alarm_names: list[str] = []
    paginator = cfn.get_paginator("list_stack_resources")
    for page in paginator.paginate(StackName=stack_name):
        for r in page.get("StackResourceSummaries", []):
            if r.get("ResourceType") == "AWS::CloudWatch::Alarm":
                phys = r.get("PhysicalResourceId")
                if phys:
                    alarm_names.append(phys)

    if not alarm_names:
        return AlarmSummary(alarms=[])

    raw_alarms: list[dict] = []
    for i in range(0, len(alarm_names), 100):
        batch = alarm_names[i : i + 100]
        resp = cw.describe_alarms(AlarmNames=batch)
        raw_alarms.extend(resp.get("MetricAlarms", []))
        raw_alarms.extend(resp.get("CompositeAlarms", []))

    return AlarmSummary(alarms=[parse_alarm(r) for r in raw_alarms])


def add_alarms_subcommand(subparsers: Any) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        "alarms", help="Show CloudWatch alarms associated with a stack"
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--no-color", action="store_true", default=False)
    p.add_argument("--json", dest="output_json", action="store_true", default=False)
    p.set_defaults(func=cmd_alarms)


def cmd_alarms(args: argparse.Namespace) -> int:
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    summary = _fetch_alarms(session, args.stack)
    fmt = "json" if args.output_json else "plain"
    print(format_alarm_summary(summary, color=not args.no_color, fmt=fmt))
    return 0
