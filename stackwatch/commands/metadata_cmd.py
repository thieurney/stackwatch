"""Command to display CloudFormation stack metadata."""
from __future__ import annotations

import argparse
import json
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack


def add_metadata_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("metadata", help="Show stack metadata")
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output as JSON",
    )
    p.add_argument(
        "--key",
        default=None,
        metavar="KEY",
        help="Print only the value of a specific metadata key",
    )
    p.set_defaults(func=cmd_metadata)


def _fetch_metadata(stack_name: str, region: str | None, profile: str | None) -> dict[str, Any] | None:
    session = boto3.Session(region_name=region, profile_name=profile)
    cf = session.client("cloudformation")
    try:
        resp = cf.get_template(StackName=stack_name, TemplateStage="Original")
        template_body = resp.get("TemplateBody", "")
        if isinstance(template_body, str):
            import yaml  # optional dep; fall back gracefully
            try:
                parsed = yaml.safe_load(template_body)
            except Exception:
                parsed = json.loads(template_body)
        else:
            parsed = template_body
        return parsed.get("Metadata") if isinstance(parsed, dict) else None
    except cf.exceptions.ClientError:
        return None


def cmd_metadata(args: argparse.Namespace) -> int:
    state = fetch_stack(args.stack, region=args.region, profile=args.profile)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    metadata = _fetch_metadata(args.stack, region=args.region, profile=getattr(args, "profile", None))

    if not metadata:
        print("No metadata found for this stack.")
        return 0

    if args.key:
        if args.key not in metadata:
            print(f"Key '{args.key}' not found in metadata.")
            return 1
        value = metadata[args.key]
        print(json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value))
        return 0

    if args.output_json:
        print(json.dumps(metadata, indent=2, default=str))
        return 0

    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            print(f"{key}:")
            print(json.dumps(value, indent=4, default=str))
        else:
            print(f"{key}: {value}")

    return 0
