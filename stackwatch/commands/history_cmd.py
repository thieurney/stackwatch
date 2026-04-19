"""Commands for viewing snapshot history for a stack."""
from __future__ import annotations

import argparse
from typing import Optional

from stackwatch.snapshot import list_snapshots, load_snapshot
from stackwatch.differ import diff_stacks, has_changes
from stackwatch.formatter import format_stack_diff, format_no_data


def add_history_subcommands(subparsers) -> None:
    p = subparsers.add_parser("history", help="Show snapshot history for a stack")
    p.add_argument("stack_name", help="Stack name")
    p.add_argument("--dir", dest="snapshot_dir", default=".stackwatch",
                   help="Snapshot directory (default: .stackwatch)")
    p.add_argument("--limit", type=int, default=10,
                   help="Max number of snapshots to show (default: 10)")
    p.add_argument("--diff", action="store_true",
                   help="Show diff between consecutive snapshots")
    p.add_argument("--no-color", action="store_true", help="Disable color output")
    p.set_defaults(func=cmd_history)


def cmd_history(args: argparse.Namespace) -> int:
    snapshots = list_snapshots(args.stack_name, snapshot_dir=args.snapshot_dir)

    if not snapshots:
        print(format_no_data(args.stack_name))
        return 0

    limited = snapshots[-args.limit:]
    print(f"Snapshots for '{args.stack_name}' ({len(limited)} of {len(snapshots)} shown):")
    for label in limited:
        print(f"  {label}")

    if args.diff and len(limited) >= 2:
        print()
        color = not args.no_color
        for older_label, newer_label in zip(limited, limited[1:]):
            older = load_snapshot(args.stack_name, older_label,
                                  snapshot_dir=args.snapshot_dir)
            newer = load_snapshot(args.stack_name, newer_label,
                                  snapshot_dir=args.snapshot_dir)
            if older is None or newer is None:
                continue
            diff = diff_stacks(older, newer)
            if has_changes(diff):
                print(f"--- {older_label}")
                print(f"+++ {newer_label}")
                print(format_stack_diff(diff, color=color))
                print()

    return 0
