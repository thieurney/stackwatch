"""CLI subcommands for stack pinning."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from stackwatch.fetcher import fetch_stack
from stackwatch.pinning import (
    PinnedStack,
    format_registry_plain,
    load_registry,
    save_registry,
)


def add_pinning_subcommands(subparsers, pin_file: str) -> None:
    p = subparsers.add_parser("pin", help="Pin/unpin stacks")
    sub = p.add_subparsers(dest="pin_action", required=True)

    add_p = sub.add_parser("add", help="Pin a stack")
    add_p.add_argument("stack_name")
    add_p.add_argument("--region", required=True)
    add_p.add_argument("--reason", default=None)
    add_p.add_argument("--pin-file", default=pin_file)

    rm_p = sub.add_parser("remove", help="Unpin a stack")
    rm_p.add_argument("stack_name")
    rm_p.add_argument("--region", required=True)
    rm_p.add_argument("--pin-file", default=pin_file)

    ls_p = sub.add_parser("list", help="List pinned stacks")
    ls_p.add_argument("--json", dest="as_json", action="store_true")
    ls_p.add_argument("--pin-file", default=pin_file)

    chk_p = sub.add_parser("check", help="Check if a stack is pinned")
    chk_p.add_argument("stack_name")
    chk_p.add_argument("--region", required=True)
    chk_p.add_argument("--pin-file", default=pin_file)


def cmd_pin_add(args, session=None, print_fn=print) -> int:
    registry = load_registry(args.pin_file)
    if registry.is_pinned(args.stack_name, args.region):
        print_fn(f"{args.stack_name} ({args.region}) is already pinned.")
        return 0
    entry = PinnedStack(
        stack_name=args.stack_name,
        region=args.region,
        reason=getattr(args, "reason", None),
        pinned_at=datetime.now(timezone.utc).isoformat(),
    )
    registry.add(entry)
    save_registry(registry, args.pin_file)
    print_fn(f"Pinned {args.stack_name} ({args.region}).")
    return 0


def cmd_pin_remove(args, session=None, print_fn=print) -> int:
    registry = load_registry(args.pin_file)
    removed = registry.remove(args.stack_name, args.region)
    if not removed:
        print_fn(f"{args.stack_name} ({args.region}) was not pinned.")
        return 1
    save_registry(registry, args.pin_file)
    print_fn(f"Unpinned {args.stack_name} ({args.region}).")
    return 0


def cmd_pin_list(args, session=None, print_fn=print) -> int:
    registry = load_registry(args.pin_file)
    if getattr(args, "as_json", False):
        data = [
            {"stack_name": e.stack_name, "region": e.region,
             "reason": e.reason, "pinned_at": e.pinned_at}
            for e in registry.entries
        ]
        print_fn(json.dumps(data, indent=2))
    else:
        print_fn(format_registry_plain(registry))
    return 0


def cmd_pin_check(args, session=None, print_fn=print) -> int:
    registry = load_registry(args.pin_file)
    entry = registry.get(args.stack_name, args.region)
    if entry:
        msg = f"PINNED: {args.stack_name} ({args.region})"
        if entry.reason:
            msg += f" — {entry.reason}"
        print_fn(msg)
        return 0
    print_fn(f"NOT PINNED: {args.stack_name} ({args.region})")
    return 1
