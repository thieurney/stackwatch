"""Command to estimate CloudFormation stack costs via the AWS Cost Estimator URL."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError


@dataclass
class EstimatorResult:
    stack_name: str
    region: str
    template_url: Optional[str]
    estimator_url: Optional[str]


def _fetch_estimator_url(client, stack_name: str) -> Optional[str]:
    """Call estimate_template_cost with the stack's current template body."""
    try:
        template_resp = client.get_template(
            StackName=stack_name,
            TemplateStage="Original",
        )
        body = template_resp.get("TemplateBody", "")
        if not body:
            return None
        resp = client.estimate_template_cost(TemplateBody=body)
        return resp.get("Url")
    except ClientError:
        return None


def add_estimator_subcommand(subparsers) -> None:
    p = subparsers.add_parser(
        "estimate",
        help="Generate an AWS cost estimator URL for a stack's template.",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="json_output", action="store_true", help="JSON output")
    p.set_defaults(func=cmd_estimator)


def cmd_estimator(args, session=None) -> int:
    if session is None:
        session = boto3.Session(
            region_name=getattr(args, "region", None),
            profile_name=getattr(args, "profile", None),
        )

    region = session.region_name or "us-east-1"
    client = session.client("cloudformation", region_name=region)

    try:
        client.describe_stacks(StackName=args.stack)
    except ClientError:
        print(f"Stack '{args.stack}' not found.")
        return 1

    url = _fetch_estimator_url(client, args.stack)

    result = EstimatorResult(
        stack_name=args.stack,
        region=region,
        template_url=None,
        estimator_url=url,
    )

    if getattr(args, "json_output", False):
        print(json.dumps({
            "stack": result.stack_name,
            "region": result.region,
            "estimator_url": result.estimator_url,
        }, indent=2))
    else:
        if result.estimator_url:
            print(f"Stack  : {result.stack_name}")
            print(f"Region : {result.region}")
            print(f"URL    : {result.estimator_url}")
        else:
            print(f"No estimator URL available for stack '{result.stack_name}'.")
            print("Tip: ensure the template is non-empty and the IAM permissions allow estimate_template_cost.")

    return 0
