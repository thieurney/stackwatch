"""CLI command for tag compliance analysis."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import format_no_data
from stackwatch.tagging import build_tagging_report, compliant, format_tagging_report


def add_tagging_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("tagging", help="Analyze tag compliance for a stack")
    p.add_argument("stack_name", help="CloudFormation stack name")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument(
        "--required-tags",
        nargs="+",
        metavar="KEY",
        default=None,
        help="Override the required tag keys (default: Environment Owner Project)",
    )
    p.add_argument(
        "--format",
        choices=["plain", "json"],
        default="plain",
        dest="fmt",
    )
    p.add_argument("--no-color", action="store_true", default=False)
    p.add_argument(
        "--fail-on-noncompliant",
        action="store_true",
        default=False,
        help="Exit with code 2 if stack is not tag-compliant",
    )
    p.set_defaults(func=cmd_tagging)


def cmd_tagging(args: argparse.Namespace) -> int:
    import boto3

    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    state = fetch_stack(session, args.stack_name)

    if state is None:
        print(format_no_data(args.stack_name))
        return 1

    report = build_tagging_report(state, required_keys=args.required_tags)
    print(format_tagging_report(report, color=not args.no_color, fmt=args.fmt))

    if args.fail_on_noncompliant and not compliant(report):
        return 2

    return 0
