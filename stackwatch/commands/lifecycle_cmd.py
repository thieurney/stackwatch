"""CLI command: `stackwatch lifecycle` — show stack age and lifecycle bucket."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.lifecycle import build_lifecycle, format_lifecycle


def add_lifecycle_subcommand(subparsers: argparse.Action) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "lifecycle",
        help="Show creation date, last-update date, and age bucket for a stack.",
    )
    p.add_argument("stack", help="CloudFormation stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--json", dest="output_json", action="store_true", help="Output as JSON"
    )
    p.add_argument(
        "--no-color", dest="no_color", action="store_true", help="Disable ANSI color"
    )
    p.set_defaults(func=cmd_lifecycle)


def cmd_lifecycle(args: argparse.Namespace) -> int:
    session = boto3.Session(
        region_name=args.region,
        profile_name=args.profile,
    )
    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"[error] Stack '{args.stack}' not found.", file=sys.stderr)
        return 1

    info = build_lifecycle(state)

    if args.output_json:
        payload: dict[str, Any] = {
            "stack_name": info.stack_name,
            "created_at": info.created_at.isoformat() if info.created_at else None,
            "last_updated_at": (
                info.last_updated_at.isoformat() if info.last_updated_at else None
            ),
            "age_days": info.age_days,
            "update_age_days": info.update_age_days,
            "age_bucket": info.age_bucket,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_lifecycle(info, use_color=not args.no_color))

    return 0
