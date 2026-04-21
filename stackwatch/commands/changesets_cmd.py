import json
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ChangeSetSummary:
    name: str
    status: str
    status_reason: Optional[str]
    creation_time: str
    description: Optional[str]


def _fetch_changesets(stack_name: str, region: str) -> List[ChangeSetSummary]:
    client = boto3.client("cloudformation", region_name=region)
    try:
        paginator = client.get_paginator("list_change_sets")
        results = []
        for page in paginator.paginate(StackName=stack_name):
            for item in page.get("Summaries", []):
                results.append(
                    ChangeSetSummary(
                        name=item["ChangeSetName"],
                        status=item["Status"],
                        status_reason=item.get("StatusReason"),
                        creation_time=str(item["CreationTime"]),
                        description=item.get("Description"),
                    )
                )
        return results
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("ValidationError", "StackNotFoundException"):
            return []
        raise


def add_changesets_subcommand(subparsers) -> None:
    parser = subparsers.add_parser("changesets", help="List pending change sets for a stack")
    parser.add_argument("stack", help="Stack name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    parser.set_defaults(func=cmd_changesets)


def cmd_changesets(args, out) -> int:
    changesets = _fetch_changesets(args.stack, args.region)

    if not changesets:
        out.write(f"No change sets found for stack '{args.stack}'.\n")
        return 0

    if args.as_json:
        data = [
            {
                "name": cs.name,
                "status": cs.status,
                "status_reason": cs.status_reason,
                "creation_time": cs.creation_time,
                "description": cs.description,
            }
            for cs in changesets
        ]
        out.write(json.dumps(data, indent=2) + "\n")
        return 0

    out.write(f"Change sets for stack '{args.stack}':\n")
    for cs in changesets:
        out.write(f"  {cs.name}  [{cs.status}]  {cs.creation_time}\n")
        if cs.description:
            out.write(f"    Description: {cs.description}\n")
        if cs.status_reason:
            out.write(f"    Reason: {cs.status_reason}\n")
    return 0
