"""CLI command: stackwatch anomaly — detect anomalies in a stack."""
from __future__ import annotations

import json
import argparse
from typing import Any, Dict

from stackwatch.fetcher import fetch_stack
from stackwatch.anomaly import build_anomaly_report, format_anomaly_report


def add_anomaly_subcommand(subparsers: Any) -> None:
    p: argparse.ArgumentParser = subparsers.add_parser(
        "anomaly",
        help="Detect anomalies in a CloudFormation stack.",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--json", dest="json_output", action="store_true", help="JSON output")
    p.add_argument("--no-color", action="store_true", help="Disable color")
    p.set_defaults(func=cmd_anomaly)


def _report_to_dict(report: Any) -> Dict[str, Any]:
    return {
        "stack_name": report.stack_name,
        "has_anomalies": report.has_anomalies,
        "high_count": report.high_count,
        "medium_count": report.medium_count,
        "findings": [
            {"severity": f.severity, "code": f.code, "message": f.message}
            for f in report.findings
        ],
    }


def cmd_anomaly(args: argparse.Namespace, session: Any) -> int:
    state = fetch_stack(args.stack, session=session)
    if state is None:
        print(f"Stack not found: {args.stack}")
        return 1

    report = build_anomaly_report(state)

    if args.json_output:
        print(json.dumps(_report_to_dict(report), indent=2))
    else:
        print(format_anomaly_report(report, color=not args.no_color))

    return 1 if report.high_count > 0 else 0
