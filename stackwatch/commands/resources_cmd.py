"""Command to list resources in a CloudFormation stack."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import List, Optional

import boto3

from stackwatch.fetcher import StackState


@dataclass
class StackResource:
    logical_id: str
    physical_id: Optional[str]
    resource_type: str
    status: str


def _fetch_resources(stack_name: str, region: str) -> Optional[List[StackResource]]:
    """Return resources for *stack_name* or None if the stack does not exist."""
    client = boto3.client("cloudformation", region_name=region)
    try:
        paginator = client.get_paginator("list_stack_resources")
        resources: List[StackResource] = []
        for page in paginator.paginate(StackName=stack_name):
            for item in page.get("StackResourceSummaries", []):
                resources.append(
                    StackResource(
                        logical_id=item["LogicalResourceId"],
                        physical_id=item.get("PhysicalResourceId"),
                        resource_type=item["ResourceType"],
                        status=item["ResourceStatus"],
                    )
                )
        return resources
    except client.exceptions.ClientError as exc:
        if "does not exist" in str(exc):
            return None
        raise


def add_resources_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("resources", help="List resources in a stack")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--filter-type", dest="filter_type", default=None,
                   help="Only show resources whose type contains this string")
    p.add_argument("--json", dest="output_json", action="store_true",
                   help="Output as JSON")
    p.set_defaults(func=cmd_resources)


def cmd_resources(args: argparse.Namespace) -> int:
    resources = _fetch_resources(args.stack, args.region)
    if resources is None:
        print(f"Stack '{args.stack}' not found in region '{args.region}'.")
        return 1

    if args.filter_type:
        resources = [r for r in resources if args.filter_type.lower() in r.resource_type.lower()]

    if not resources:
        print("No resources found.")
        return 0

    if args.output_json:
        payload = [
            {
                "LogicalId": r.logical_id,
                "PhysicalId": r.physical_id,
                "Type": r.resource_type,
                "Status": r.status,
            }
            for r in resources
        ]
        print(json.dumps(payload, indent=2))
        return 0

    col_w = [max(len(r.logical_id) for r in resources),
             max(len(r.resource_type) for r in resources),
             max(len(r.status) for r in resources)]
    header = f"{'LOGICAL ID':<{col_w[0]}}  {'TYPE':<{col_w[1]}}  {'STATUS':<{col_w[2]}}  PHYSICAL ID"
    print(header)
    print("-" * (len(header) + 20))
    for r in resources:
        phys = r.physical_id or "-"
        print(f"{r.logical_id:<{col_w[0]}}  {r.resource_type:<{col_w[1]}}  {r.status:<{col_w[2]}}  {phys}")
    return 0
