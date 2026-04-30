"""CLI command: stackwatch ownership — show stack owner/team metadata."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.ownership import build_ownership_info, format_ownership_plain


def add_ownership_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("ownership", help="Show owner/team tags for a stack")
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(func=cmd_ownership)


def cmd_ownership(args: argparse.Namespace) -> int:
    import boto3

    session = boto3.Session(
        region_name=args.region,
        profile_name=getattr(args, "profile", None),
    )
    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"error: stack '{args.stack}' not found", file=sys.stderr)
        return 1

    info = build_ownership_info(state)

    if args.as_json:
        data = {
            "stack_name": info.stack_name,
            "owner": info.owner,
            "team": info.team,
            "environment": info.environment,
            "is_owned": info.is_owned,
            "extra_tags": info.extra_tags,
        }
        print(json.dumps(data, indent=2))
    else:
        print(format_ownership_plain(info))

    return 0
