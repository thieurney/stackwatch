"""CLI sub-command: stackwatch ownership <stack> [--profile] [--region] [--json]"""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace

from stackwatch.fetcher import fetch_stack
from stackwatch.ownership import build_ownership_info, format_ownership_info


def add_ownership_subcommand(sub: ArgumentParser) -> None:
    p = sub.add_parser("ownership", help="Show owner metadata for a stack")
    p.add_argument("stack", help="CloudFormation stack name")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", default=False)
    p.add_argument("--no-color", dest="no_color", action="store_true", default=False)
    p.set_defaults(func=cmd_ownership)


def cmd_ownership(args: Namespace) -> int:
    import boto3

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    state = fetch_stack(session, args.stack)

    if state is None:
        print(f"[error] stack '{args.stack}' not found.", file=sys.stderr)
        return 1

    info = build_ownership_info(state)

    if args.as_json:
        payload = {
            "stack_name": info.stack_name,
            "owner": info.owner,
            "team": info.team,
            "cost_center": info.cost_center,
            "is_complete": info.is_complete,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_ownership_info(info, use_color=not args.no_color))
        if not info.is_complete:
            missing = [
                k
                for k, v in [
                    ("owner", info.owner),
                    ("team", info.team),
                    ("cost_center", info.cost_center),
                ]
                if v is None
            ]
            print(f"\nWarning: incomplete ownership — missing: {', '.join(missing)}",
                  file=sys.stderr)

    return 0
