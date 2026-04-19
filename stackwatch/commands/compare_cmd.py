"""compare command: diff two live stacks across environments."""
from __future__ import annotations

import argparse
from typing import Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.differ import diff_stacks, has_changes
from stackwatch.formatter import format_stack_diff, format_no_data


def add_compare_subcommand(subparsers) -> None:
    p = subparsers.add_parser(
        "compare",
        help="Compare a CloudFormation stack between two environments/regions.",
    )
    p.add_argument("stack_name", help="Name of the CloudFormation stack.")
    p.add_argument("--env-a", required=True, help="First AWS profile name.")
    p.add_argument("--env-b", required=True, help="Second AWS profile name.")
    p.add_argument("--region-a", default=None, help="AWS region for env-a.")
    p.add_argument("--region-b", default=None, help="AWS region for env-b.")
    p.add_argument("--no-color", action="store_true", help="Disable colored output.")
    p.set_defaults(func=cmd_compare)


def cmd_compare(args: argparse.Namespace) -> int:
    state_a = fetch_stack(
        stack_name=args.stack_name,
        profile=args.env_a,
        region=args.region_a,
    )
    state_b = fetch_stack(
        stack_name=args.stack_name,
        profile=args.env_b,
        region=args.region_b,
    )

    if state_a is None and state_b is None:
        print(format_no_data(args.stack_name))
        return 1

    label_a = f"{args.env_a}" + (f"/{args.region_a}" if args.region_a else "")
    label_b = f"{args.env_b}" + (f"/{args.region_b}" if args.region_b else "")

    diff = diff_stacks(state_a, state_b)
    color = not args.no_color
    print(format_stack_diff(diff, label_old=label_a, label_new=label_b, color=color))
    return 0 if not has_changes(diff) else 2
