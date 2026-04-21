"""Command to display a summary status table for one or more stacks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

import boto3

from stackwatch.fetcher import StackState, fetch_stack


@dataclass
class StatusRow:
    stack_name: str
    status: str
    region: str
    drift: Optional[str]
    termination_protection: bool


_STATUS_COLORS = {
    "CREATE_COMPLETE": "\033[32m",
    "UPDATE_COMPLETE": "\033[32m",
    "DELETE_COMPLETE": "\033[31m",
    "ROLLBACK_COMPLETE": "\033[33m",
    "CREATE_FAILED": "\033[31m",
    "UPDATE_FAILED": "\033[31m",
    "UPDATE_ROLLBACK_COMPLETE": "\033[33m",
}
_RESET = "\033[0m"


def _colorize(status: str, use_color: bool) -> str:
    if not use_color:
        return status
    color = _STATUS_COLORS.get(status, "")
    return f"{color}{status}{_RESET}" if color else status


def _build_row(state: StackState, region: str) -> StatusRow:
    raw = state.raw or {}
    return StatusRow(
        stack_name=state.stack_name,
        status=state.status,
        region=region,
        drift=raw.get("DriftInformation", {}).get("StackDriftStatus"),
        termination_protection=raw.get("EnableTerminationProtection", False),
    )


def _format_table(rows: List[StatusRow], use_color: bool) -> str:
    header = f"{'STACK':<40} {'STATUS':<30} {'REGION':<15} {'DRIFT':<15} {'PROT'}"
    sep = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        status_str = _colorize(r.status, use_color)
        drift_str = r.drift or "N/A"
        prot_str = "yes" if r.termination_protection else "no"
        lines.append(f"{r.stack_name:<40} {status_str:<30} {r.region:<15} {drift_str:<15} {prot_str}")
    return "\n".join(lines)


def add_status_subcommand(subparsers) -> None:
    p = subparsers.add_parser("status", help="Show status summary for one or more stacks")
    p.add_argument("stacks", nargs="+", help="Stack names to query")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.add_argument("--no-color", dest="no_color", action="store_true", help="Disable color output")
    p.set_defaults(func=cmd_status)


def cmd_status(args) -> int:
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    region = session.region_name or "us-east-1"
    rows: List[StatusRow] = []
    missing: List[str] = []

    for name in args.stacks:
        state = fetch_stack(session, name)
        if state is None:
            missing.append(name)
        else:
            rows.append(_build_row(state, region))

    if missing:
        for m in missing:
            print(f"[not found] {m}")

    if not rows:
        print("No stacks found.")
        return 1

    if args.as_json:
        data = [
            {
                "stack_name": r.stack_name,
                "status": r.status,
                "region": r.region,
                "drift": r.drift,
                "termination_protection": r.termination_protection,
            }
            for r in rows
        ]
        print(json.dumps(data, indent=2))
    else:
        print(_format_table(rows, use_color=not args.no_color))

    return 0
