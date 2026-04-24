"""CLI command: stackwatch rollup — show a rolled-up report for multiple stacks."""
from __future__ import annotations

import argparse
from typing import List

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.rollup import build_rollup, format_rollup


def add_rollup_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("rollup", help="Aggregate status across multiple stacks")
    p.add_argument("stacks", nargs="+", metavar="STACK", help="Stack names to include")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    p.add_argument("--no-color", action="store_true", help="Disable ANSI colour")
    p.set_defaults(func=cmd_rollup)


def cmd_rollup(args: argparse.Namespace) -> int:
    session = boto3.Session(
        region_name=args.region,
        profile_name=getattr(args, "profile", None),
    )

    states = []
    missing: List[str] = []

    for stack_name in args.stacks:
        state = fetch_stack(session, stack_name)
        if state is None:
            missing.append(stack_name)
        else:
            states.append(state)

    if missing:
        for name in missing:
            print(f"[warn] stack not found: {name}")

    if not states:
        print("No stacks found.")
        return 1

    report = build_rollup(states)
    fmt = "json" if args.json_output else "plain"
    print(format_rollup(report, color=not args.no_color, fmt=fmt))
    return 0
