"""CLI sub-command handlers for snapshot operations."""

from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace

from stackwatch.fetcher import fetch_stack
from stackwatch.snapshot import save_snapshot, load_snapshot, list_snapshots
from stackwatch.differ import diff_stacks, has_changes
from stackwatch.formatter import format_stack_diff, format_no_data


def add_snapshot_subcommands(subparsers) -> None:
    """Register snapshot-related sub-commands onto an existing subparsers action."""

    # --- save ---
    p_save: ArgumentParser = subparsers.add_parser(
        "snapshot-save", help="Fetch a stack and save its state as a named snapshot."
    )
    p_save.add_argument("stack_name", help="CloudFormation stack name")
    p_save.add_argument("label", help="Snapshot label (e.g. 'baseline', 'before-deploy')")
    p_save.add_argument("--region", default=None)
    p_save.add_argument("--profile", default=None)
    p_save.add_argument("--dir", dest="directory", default=None)
    p_save.set_defaults(func=cmd_snapshot_save)

    # --- diff ---
    p_diff: ArgumentParser = subparsers.add_parser(
        "snapshot-diff", help="Diff live stack state against a saved snapshot."
    )
    p_diff.add_argument("stack_name", help="CloudFormation stack name")
    p_diff.add_argument("label", help="Snapshot label to compare against")
    p_diff.add_argument("--region", default=None)
    p_diff.add_argument("--profile", default=None)
    p_diff.add_argument("--dir", dest="directory", default=None)
    p_diff.add_argument("--no-color", action="store_true")
    p_diff.set_defaults(func=cmd_snapshot_diff)

    # --- list ---
    p_list: ArgumentParser = subparsers.add_parser(
        "snapshot-list", help="List all saved snapshots."
    )
    p_list.add_argument("--dir", dest="directory", default=None)
    p_list.set_defaults(func=cmd_snapshot_list)


def _dir_kwargs(args: Namespace) -> dict:
    return {"directory": args.directory} if args.directory else {}


def cmd_snapshot_save(args: Namespace) -> int:
    state = fetch_stack(args.stack_name, region=args.region, profile=args.profile)
    if state is None:
        print(format_no_data(args.stack_name))
        return 1
    path = save_snapshot(state, args.label, **_dir_kwargs(args))
    print(f"Snapshot saved: {path}")
    return 0


def cmd_snapshot_diff(args: Namespace) -> int:
    snapshot = load_snapshot(args.stack_name, args.label, **_dir_kwargs(args))
    if snapshot is None:
        print(f"No snapshot found for '{args.stack_name}' with label '{args.label}'.")
        return 1
    live = fetch_stack(args.stack_name, region=args.region, profile=args.profile)
    if live is None:
        print(format_no_data(args.stack_name))
        return 1
    diff = diff_stacks(snapshot, live)
    use_color = not args.no_color
    print(format_stack_diff(diff, color=use_color))
    return 1 if has_changes(diff) else 0


def cmd_snapshot_list(args: Namespace) -> int:
    snapshots = list_snapshots(**_dir_kwargs(args))
    if not snapshots:
        print("No snapshots found.")
        return 0
    print(f"{'STACK':<35} {'LABEL':<20} {'STATUS':<25} SAVED AT")
    print("-" * 95)
    for s in snapshots:
        print(f"{s['stack_name']:<35} {s['label']:<20} {s['status']:<25} {s['saved_at']}")
    return 0
