import time
import sys
from argparse import _SubParsersAction
from typing import Optional

from stackwatch.fetcher import fetch_stack, StackState
from stackwatch.differ import diff_stacks, has_changes
from stackwatch.formatter import format_stack_diff, format_no_data


def add_watch_subcommand(subparsers: _SubParsersAction) -> None:
    p = subparsers.add_parser("watch", help="Poll a stack and print diffs on change")
    p.add_argument("stack_name", help="CloudFormation stack name")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--interval",
        type=int,
        default=30,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 30)",
    )
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    p.set_defaults(func=cmd_watch)


def cmd_watch(args) -> int:
    color = not args.no_color
    interval: int = args.interval
    stack_name: str = args.stack_name

    print(
        f"Watching '{stack_name}' every {interval}s — press Ctrl+C to stop.",
        flush=True,
    )

    previous: Optional[StackState] = None

    try:
        while True:
            current = fetch_stack(
                stack_name,
                region=args.region,
                profile=args.profile,
            )

            if current is None:
                print(format_no_data(stack_name))
            elif previous is None:
                print(f"[initial] status={current.status}  resources={len(current.resources)}", flush=True)
            else:
                diff = diff_stacks(previous, current)
                if has_changes(diff):
                    print(format_stack_diff(diff, color=color), flush=True)
                else:
                    print("[no change]", flush=True)

            previous = current
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatch stopped.", flush=True)

    return 0
