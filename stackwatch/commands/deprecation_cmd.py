"""CLI command: stackwatch deprecation <stack> [--profile] [--region] [--json]"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from stackwatch.deprecation import build_deprecation_report, format_deprecation_report
from stackwatch.fetcher import fetch_stack


def add_deprecation_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "deprecation",
        help="Report deprecated runtime features or states for a stack.",
    )
    p.add_argument("stack", help="CloudFormation stack name or ARN.")
    p.add_argument("--profile", default=None, help="AWS profile name.")
    p.add_argument("--region", default=None, help="AWS region.")
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON.")
    p.add_argument("--no-color", dest="no_color", action="store_true", help="Disable ANSI color.")
    p.set_defaults(func=cmd_deprecation)


def _report_to_dict(report) -> Dict[str, Any]:
    return {
        "stack_name": report.stack_name,
        "has_warnings": report.has_warnings,
        "high_count": report.high_count,
        "warnings": [
            {"code": w.code, "severity": w.severity, "message": w.message}
            for w in report.warnings
        ],
    }


def cmd_deprecation(args: argparse.Namespace) -> int:
    state = fetch_stack(args.stack, profile=args.profile, region=args.region)
    if state is None:
        print(f"Stack '{args.stack}' not found.", file=sys.stderr)
        return 1

    report = build_deprecation_report(state)

    if args.as_json:
        print(json.dumps(_report_to_dict(report), indent=2))
        return 0

    use_color = not getattr(args, "no_color", False)
    print(format_deprecation_report(report, color=use_color))
    return 0
