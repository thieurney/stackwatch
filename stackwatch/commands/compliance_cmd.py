"""CLI command: stackwatch compliance — check stack compliance rules."""
from __future__ import annotations

import argparse
import sys
from typing import Optional

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.compliance import build_compliance_report, format_compliance_report
from stackwatch.formatter import format_no_data


def add_compliance_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser(
        "compliance",
        help="Check compliance rules for a stack",
    )
    parser.add_argument("stack", help="CloudFormation stack name")
    parser.add_argument("--region", default=None, help="AWS region")
    parser.add_argument("--profile", default=None, help="AWS profile")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit with code 2 if any compliance rule fails",
    )
    parser.set_defaults(func=cmd_compliance)


def cmd_compliance(args: argparse.Namespace) -> int:
    session = boto3.Session(
        region_name=getattr(args, "region", None),
        profile_name=getattr(args, "profile", None),
    )
    state = fetch_stack(args.stack, session)

    if state is None:
        print(format_no_data(args.stack))
        return 1

    report = build_compliance_report(state)
    color = not getattr(args, "no_color", False)
    json_output = getattr(args, "json_output", False)

    print(format_compliance_report(report, color=color, json_output=json_output))

    if getattr(args, "fail_on_violation", False) and not report.compliant:
        return 2

    return 0
