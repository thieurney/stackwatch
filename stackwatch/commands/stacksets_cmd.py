"""Command to inspect CloudFormation StackSet instances and their statuses."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StackSetInstance:
    account: str
    region: str
    status: str
    status_reason: Optional[str]
    stack_id: Optional[str]


def _fetch_stackset_instances(session, stackset_name: str) -> List[StackSetInstance]:
    cf = session.client("cloudformation")
    paginator = cf.get_paginator("list_stack_instances")
    instances: List[StackSetInstance] = []
    for page in paginator.paginate(StackSetName=stackset_name):
        for item in page.get("Summaries", []):
            instances.append(
                StackSetInstance(
                    account=item.get("Account", ""),
                    region=item.get("Region", ""),
                    status=item.get("Status", "UNKNOWN"),
                    status_reason=item.get("StatusReason"),
                    stack_id=item.get("StackId"),
                )
            )
    return instances


def _format_instances(instances: List[StackSetInstance], use_json: bool) -> str:
    if use_json:
        return json.dumps(
            [
                {
                    "account": i.account,
                    "region": i.region,
                    "status": i.status,
                    "status_reason": i.status_reason,
                    "stack_id": i.stack_id,
                }
                for i in instances
            ],
            indent=2,
        )
    lines = []
    for i in instances:
        reason = f"  reason: {i.status_reason}" if i.status_reason else ""
        lines.append(f"  {i.account} / {i.region}  [{i.status}]{reason}")
    return "\n".join(lines) if lines else "  (no instances found)"


def add_stacksets_subcommand(subparsers):
    p = subparsers.add_parser("stacksets", help="List instances of a StackSet")
    p.add_argument("stackset_name", help="Name of the CloudFormation StackSet")
    p.add_argument("--json", dest="use_json", action="store_true", help="Output as JSON")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.set_defaults(func=cmd_stacksets)


def cmd_stacksets(args, session) -> int:
    try:
        instances = _fetch_stackset_instances(session, args.stackset_name)
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
        return 1

    if not instances:
        print(f"No instances found for StackSet '{args.stackset_name}'.")
        return 0

    print(f"StackSet: {args.stackset_name}  ({len(instances)} instance(s))")
    print(_format_instances(instances, getattr(args, "use_json", False)))
    return 0
