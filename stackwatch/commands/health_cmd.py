"""CLI command: stackwatch health — show stack health score."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from stackwatch.fetcher import fetch_stack
from stackwatch.health import build_health_report, format_health_report


def add_health_subcommand(subparsers: Any) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        "health",
        help="Show a health score for a CloudFormation stack",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--json", dest="json_output", action="store_true", help="Output as JSON"
    )
    p.add_argument(
        "--no-color", dest="no_color", action="store_true", help="Disable colour output"
    )
    p.set_defaults(func=cmd_health)


def cmd_health(args: argparse.Namespace) -> int:
    state = fetch_stack(
        args.stack,
        region=args.region,
        profile=getattr(args, "profile", None),
    )
    if state is None:
        print(f"Stack not found: {args.stack}", file=sys.stderr)
        return 1

    # Determine drift — stored as string in StackState.extra if present
    drift_status = (state.extra or {}).get("drift_status", "NOT_CHECKED")
    drifted = drift_status == "DRIFTED"

    alarm_count = int((state.extra or {}).get("alarm_count", 0))
    termination_protected = bool(
        (state.extra or {}).get("termination_protection", True)
    )

    report = build_health_report(
        status=state.status,
        drifted=drifted,
        alarm_count=alarm_count,
        termination_protected=termination_protected,
    )

    if getattr(args, "json_output", False):
        payload = {
            "stack": args.stack,
            "score": report.score,
            "grade": report.grade,
            "healthy": report.healthy,
            "issues": [
                {"severity": i.severity, "message": i.message}
                for i in report.issues
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        color = not getattr(args, "no_color", False)
        print(format_health_report(report, color=color))

    return 0 if report.healthy else 2
