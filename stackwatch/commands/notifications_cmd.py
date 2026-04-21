"""Command to display SNS/CloudWatch notification configurations for a stack."""
from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import List

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import format_no_data


@dataclass
class NotificationConfig:
    topic_arn: str

    @property
    def topic_name(self) -> str:
        return self.topic_arn.split(":")[-1]


def _fetch_notifications(stack_name: str, region: str) -> List[NotificationConfig]:
    client = boto3.client("cloudformation", region_name=region)
    response = client.describe_stacks(StackName=stack_name)
    stacks = response.get("Stacks", [])
    if not stacks:
        return []
    arns = stacks[0].get("NotificationARNs", [])
    return [NotificationConfig(topic_arn=arn) for arn in arns]


def _format_notifications(configs: List[NotificationConfig], use_json: bool) -> str:
    if use_json:
        return json.dumps([{"topic_arn": c.topic_arn, "topic_name": c.topic_name} for c in configs], indent=2)
    lines = []
    for c in configs:
        lines.append(f"  ARN  : {c.topic_arn}")
        lines.append(f"  Name : {c.topic_name}")
        lines.append("")
    return "\n".join(lines).rstrip()


def add_notifications_subcommand(subparsers) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        "notifications",
        help="Show SNS notification ARNs configured on a stack",
    )
    parser.add_argument("stack", help="Stack name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--profile", default=None, help="AWS profile")
    parser.add_argument("--json", dest="use_json", action="store_true", help="Output as JSON")
    parser.set_defaults(func=cmd_notifications)


def cmd_notifications(args: Namespace) -> int:
    if args.profile:
        boto3.setup_default_session(profile_name=args.profile)

    state = fetch_stack(args.stack, args.region)
    if state is None:
        print(format_no_data(args.stack, args.region))
        return 1

    configs = _fetch_notifications(args.stack, args.region)
    if not configs:
        print(f"No notification ARNs configured for stack '{args.stack}'.")
        return 0

    print(f"Notifications for '{args.stack}' ({args.region}):")
    print(_format_notifications(configs, args.use_json))
    return 0
