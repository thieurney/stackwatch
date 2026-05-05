"""CLI command: stackwatch coverage <stack> [--json]."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import List

from stackwatch.coverage import build_coverage_report, format_coverage_report
from stackwatch.fetcher import fetch_stack


def add_coverage_subcommand(sub: "_SubParsersAction") -> None:  # type: ignore[type-arg]
    p: ArgumentParser = sub.add_parser(
        "coverage",
        help="Analyse monitoring and configuration coverage for one or more stacks",
    )
    p.add_argument("stacks", nargs="+", metavar="STACK", help="Stack name(s) to analyse")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", help="JSON output")
    p.add_argument("--no-color", dest="no_color", action="store_true")
    p.set_defaults(func=cmd_coverage)


def cmd_coverage(args: Namespace) -> int:
    import boto3

    session = boto3.Session(region_name=args.region, profile_name=args.profile)

    reports = []
    missing: List[str] = []

    for stack_name in args.stacks:
        state = fetch_stack(session, stack_name)
        if state is None:
            print(f"[WARN] Stack not found: {stack_name}", file=sys.stderr)
            missing.append(stack_name)
            continue
        reports.append(build_coverage_report(state))

    if not reports:
        print("No stacks found.", file=sys.stderr)
        return 1

    if args.as_json:
        payload = [
            {
                "stack": r.stack_name,
                "score": r.score,
                "gaps": [
                    {"dimension": g.dimension, "detail": g.detail, "severity": g.severity}
                    for g in r.gaps
                ],
            }
            for r in reports
        ]
        print(json.dumps(payload, indent=2))
    else:
        color = not getattr(args, "no_color", False)
        for r in reports:
            print(format_coverage_report(r, color=color))
            print()

    any_high = any(
        g.severity == "high" for r in reports for g in r.gaps
    )
    return 1 if any_high else 0
