"""Command for viewing and toggling stack protection (termination + update)."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

import boto3

from stackwatch.fetcher import StackState, fetch_stack


@dataclass
class ProtectionStatus:
    termination_protection: bool
    update_replace_policy: Optional[str]  # derived from stack policy presence


def _fetch_protection(session: boto3.Session, stack_name: str) -> Optional[ProtectionStatus]:
    cf = session.client("cloudformation")
    try:
        resp = cf.describe_stacks(StackName=stack_name)
    except cf.exceptions.ClientError:
        return None
    stacks = resp.get("Stacks", [])
    if not stacks:
        return None
    stack = stacks[0]
    termination = stack.get("EnableTerminationProtection", False)
    return ProtectionStatus(termination_protection=termination, update_replace_policy=None)


def _toggle_termination(session: boto3.Session, stack_name: str, enable: bool) -> None:
    cf = session.client("cloudformation")
    cf.update_termination_protection(
        EnableTerminationProtection=enable,
        StackName=stack_name,
    )


def cmd_protection(args: argparse.Namespace) -> int:
    session = boto3.Session(
        region_name=args.region,
        profile_name=getattr(args, "profile", None),
    )
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    if getattr(args, "enable", False) or getattr(args, "disable", False):
        enable = args.enable
        _toggle_termination(session, args.stack, enable)
        status = "enabled" if enable else "disabled"
        print(f"Termination protection {status} for '{args.stack}'.")
        return 0

    protection = _fetch_protection(session, args.stack)
    if protection is None:
        print("Could not retrieve protection status.")
        return 1

    tp = "enabled" if protection.termination_protection else "disabled"
    print(f"Stack:                  {args.stack}")
    print(f"Termination protection: {tp}")
    return 0


def add_protection_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    parser = subparsers.add_parser(
        "protection",
        help="View or toggle stack termination protection",
    )
    parser.add_argument("stack", help="Stack name or ARN")
    parser.add_argument("--region", default=None)
    parser.add_argument("--profile", default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--enable", action="store_true", default=False,
        help="Enable termination protection",
    )
    group.add_argument(
        "--disable", action="store_true", default=False,
        help="Disable termination protection",
    )
    parser.set_defaults(func=cmd_protection)
