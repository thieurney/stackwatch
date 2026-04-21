"""Command to view and toggle termination protection on a CloudFormation stack."""
from __future__ import annotations

import argparse
import json
from typing import Any

from stackwatch.fetcher import StackState, fetch_stack


def add_termination_subcommand(subparsers: Any) -> None:
    p = subparsers.add_parser(
        "termination",
        help="Show or toggle termination protection for a stack.",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--enable",
        dest="action",
        action="store_const",
        const="enable",
        help="Enable termination protection",
    )
    p.add_argument(
        "--disable",
        dest="action",
        action="store_const",
        const="disable",
        help="Disable termination protection",
    )
    p.add_argument("--json", dest="as_json", action="store_true", help="JSON output")
    p.set_defaults(func=cmd_termination, action=None)


def _fetch_termination_status(session: Any, stack_name: str) -> bool | None:
    """Return the EnableTerminationProtection flag, or None if unavailable."""
    cf = session.client("cloudformation")
    resp = cf.describe_stacks(StackName=stack_name)
    stacks = resp.get("Stacks", [])
    if not stacks:
        return None
    return stacks[0].get("EnableTerminationProtection", False)


def _toggle_termination(session: Any, stack_name: str, enable: bool) -> None:
    cf = session.client("cloudformation")
    cf.update_termination_protection(
        EnableTerminationProtection=enable,
        StackName=stack_name,
    )


def cmd_termination(args: argparse.Namespace, session: Any) -> int:
    state: StackState | None = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    if args.action in ("enable", "disable"):
        enable = args.action == "enable"
        _toggle_termination(session, args.stack, enable)
        status_str = "enabled" if enable else "disabled"
        if args.as_json:
            print(json.dumps({"stack": args.stack, "termination_protection": enable}))
        else:
            print(f"Termination protection {status_str} for '{args.stack}'.")
        return 0

    # Read-only: show current status
    protected = _fetch_termination_status(session, args.stack)
    if args.as_json:
        print(json.dumps({"stack": args.stack, "termination_protection": protected}))
    else:
        status_str = "enabled" if protected else "disabled"
        print(f"Stack: {args.stack}")
        print(f"Termination protection: {status_str}")
    return 0
