"""Command to list and describe CloudFormation stack signals (WaitCondition signals)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack


@dataclass
class StackSignal:
    logical_resource_id: str
    status: str
    status_reason: str
    unique_id: str


def _fetch_signals(
    stack_name: str,
    logical_resource_id: str,
    session: Any,
) -> list[StackSignal]:
    cf = session.client("cloudformation")
    try:
        resp = cf.describe_stack_resource(
            StackName=stack_name,
            LogicalResourceId=logical_resource_id,
        )
    except cf.exceptions.ClientError:
        return []

    detail = resp.get("StackResourceDetail", {})
    raw = detail.get("Metadata") or detail.get("ResourceStatusReason", "")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = {}

    signals = []
    for uid, info in data.items():
        if isinstance(info, dict):
            signals.append(
                StackSignal(
                    logical_resource_id=logical_resource_id,
                    status=info.get("Status", "UNKNOWN"),
                    status_reason=info.get("Reason", ""),
                    unique_id=uid,
                )
            )
    return signals


def add_signals_subcommand(subparsers: Any) -> None:
    p = subparsers.add_parser("signals", help="Show WaitCondition signals for a stack resource")
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("resource", help="Logical resource ID of the WaitCondition")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.set_defaults(func=cmd_signals)


def cmd_signals(args: Any) -> int:
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    signals = _fetch_signals(args.stack, args.resource, session)

    if args.as_json:
        print(json.dumps([s.__dict__ for s in signals], indent=2))
        return 0

    if not signals:
        print(f"No signals found for resource '{args.resource}'.")
        return 0

    print(f"Signals for {args.resource} in {args.stack}:")
    print(f"  {'UniqueId':<36}  {'Status':<12}  Reason")
    print(f"  {'-'*36}  {'-'*12}  {'-'*30}")
    for s in signals:
        print(f"  {s.unique_id:<36}  {s.status:<12}  {s.status_reason}")
    return 0
