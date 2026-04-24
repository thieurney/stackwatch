"""CLI command: stackwatch maturity <stack> [--region] [--profile] [--json]"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.maturity import build_maturity_report, format_maturity_report


def add_maturity_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "maturity",
        help="Score a stack against operational maturity best-practices.",
    )
    p.add_argument("stack", help="CloudFormation stack name or ARN.")
    p.add_argument("--region", default=None, help="AWS region.")
    p.add_argument("--profile", default=None, help="AWS profile name.")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Emit JSON output.")
    p.add_argument("--no-color", dest="no_color", action="store_true",
                   help="Disable ANSI color codes.")
    p.set_defaults(func=cmd_maturity)


def cmd_maturity(args: argparse.Namespace) -> int:
    session = boto3.Session(
        region_name=args.region,
        profile_name=args.profile,
    )
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack not found: {args.stack}", file=sys.stderr)
        return 1

    report = build_maturity_report(state)

    if args.as_json:
        data = {
            "stack_name": report.stack_name,
            "score": report.score,
            "grade": report.grade,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "weight": c.weight,
                    "detail": c.detail,
                }
                for c in report.checks
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        use_color = not args.no_color
        print(format_maturity_report(report, color=use_color))

    return 0
