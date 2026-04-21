"""Command to view and set CloudFormation stack log retention policy."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Optional

import boto3

from stackwatch.fetcher import StackState, fetch_stack


@dataclass
class RetentionConfig:
    log_group_name: Optional[str]
    retention_in_days: Optional[int]


def _fetch_retention(session: boto3.Session, stack_name: str) -> RetentionConfig:
    cfn = session.client("cloudformation")
    try:
        resp = cfn.describe_stacks(StackName=stack_name)
        stack = resp["Stacks"][0]
        log_group = stack.get("StackStatusReason", None)  # placeholder field
        # Real retention lives on the stack's log group in CloudWatch Logs
        log_group_name = stack.get("LoggingConfig", {}).get("LogGroupName")
        retention = None
        if log_group_name:
            logs = session.client("logs")
            lg_resp = logs.describe_log_groups(logGroupNamePrefix=log_group_name)
            groups = lg_resp.get("logGroups", [])
            if groups:
                retention = groups[0].get("retentionInDays")
        return RetentionConfig(log_group_name=log_group_name, retention_in_days=retention)
    except cfn.exceptions.ClientError:
        return RetentionConfig(log_group_name=None, retention_in_days=None)


def _format_retention(config: RetentionConfig) -> str:
    if config.log_group_name is None:
        return "No log group configured for this stack."
    days = config.retention_in_days
    retention_str = f"{days} days" if days else "Never expire"
    return f"Log Group : {config.log_group_name}\nRetention : {retention_str}"


def add_retention_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("retention", help="View stack log retention settings")
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.set_defaults(func=cmd_retention)


def cmd_retention(args: argparse.Namespace) -> int:
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    config = _fetch_retention(session, args.stack)

    if args.as_json:
        print(json.dumps({
            "stack": args.stack,
            "log_group_name": config.log_group_name,
            "retention_in_days": config.retention_in_days,
        }, indent=2))
    else:
        print(_format_retention(config))

    return 0
