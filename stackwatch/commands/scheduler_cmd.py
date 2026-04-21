"""Command to inspect EventBridge Scheduler or CloudWatch Events rules associated with a stack."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError


@dataclass
class SchedulerRule:
    name: str
    schedule: Optional[str]
    state: str
    description: Optional[str]
    target_arn: Optional[str]


def _fetch_scheduler_rules(session: boto3.Session, stack_name: str) -> List[SchedulerRule]:
    client = session.client("events")
    rules: List[SchedulerRule] = []
    try:
        paginator = client.get_paginator("list_rules")
        for page in paginator.paginate():
            for rule in page.get("Rules", []):
                tags_resp = client.list_tags_for_resource(ResourceARN=rule["Arn"])
                tags = {t["Key"]: t["Value"] for t in tags_resp.get("Tags", [])}
                if tags.get("aws:cloudformation:stack-name") != stack_name:
                    continue
                targets_resp = client.list_targets_by_rule(Rule=rule["Name"])
                target_arn = None
                targets = targets_resp.get("Targets", [])
                if targets:
                    target_arn = targets[0].get("Arn")
                rules.append(SchedulerRule(
                    name=rule["Name"],
                    schedule=rule.get("ScheduleExpression"),
                    state=rule.get("State", "UNKNOWN"),
                    description=rule.get("Description"),
                    target_arn=target_arn,
                ))
    except ClientError:
        pass
    return rules


def _format_rules(rules: List[SchedulerRule], use_json: bool) -> str:
    if use_json:
        return json.dumps([r.__dict__ for r in rules], indent=2)
    if not rules:
        return "  (no EventBridge rules found for this stack)"
    lines = []
    for r in rules:
        lines.append(f"  {r.name}  [{r.state}]")
        if r.schedule:
            lines.append(f"    Schedule : {r.schedule}")
        if r.description:
            lines.append(f"    Desc     : {r.description}")
        if r.target_arn:
            lines.append(f"    Target   : {r.target_arn}")
    return "\n".join(lines)


def add_scheduler_subcommand(subparsers):
    p = subparsers.add_parser("scheduler", help="Show EventBridge rules linked to a stack")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="use_json", action="store_true")
    p.set_defaults(func=cmd_scheduler)


def cmd_scheduler(args, session: Optional[boto3.Session] = None) -> int:
    if session is None:
        session = boto3.Session(region_name=args.region, profile_name=args.profile)
    rules = _fetch_scheduler_rules(session, args.stack)
    print(_format_rules(rules, getattr(args, "use_json", False)))
    return 0
