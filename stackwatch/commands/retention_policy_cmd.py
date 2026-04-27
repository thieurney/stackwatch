"""CLI sub-commands for snapshot retention policy management."""
from __future__ import annotations

import argparse
import sys
from typing import List

from stackwatch.retention_policy import prune_by_age, prune_by_count


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------

def _dir_kwargs() -> dict:
    return {
        "default": ".stackwatch",
        "metavar": "DIR",
        "help": "snapshot directory (default: .stackwatch)",
    }


def add_retention_policy_subcommands(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "retention-policy",
        help="prune old snapshots by count or age",
    )
    rp_sub = p.add_subparsers(dest="retention_action", required=True)

    # --- prune-count ---
    pc = rp_sub.add_parser("prune-count", help="keep N most-recent snapshots")
    pc.add_argument("stack", help="stack name")
    pc.add_argument("env", help="environment label")
    pc.add_argument("--keep", type=int, default=10, help="number of snapshots to keep (default: 10)")
    pc.add_argument("--dir", dest="snapshot_dir", **_dir_kwargs())
    pc.set_defaults(func=cmd_prune_count)

    # --- prune-age ---
    pa = rp_sub.add_parser("prune-age", help="delete snapshots older than N days")
    pa.add_argument("stack", help="stack name")
    pa.add_argument("env", help="environment label")
    pa.add_argument("--days", type=int, default=30, help="max age in days (default: 30)")
    pa.add_argument("--dir", dest="snapshot_dir", **_dir_kwargs())
    pa.set_defaults(func=cmd_prune_age)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_prune_count(args: argparse.Namespace) -> int:
    result = prune_by_count(
        stack_name=args.stack,
        environment=args.env,
        keep=args.keep,
        snapshot_dir=args.snapshot_dir,
    )
    if result.removed_count == 0:
        print(f"Nothing to prune for {args.stack}/{args.env} (kept {result.kept}).")
    else:
        print(
            f"Pruned {result.removed_count} snapshot(s) for {args.stack}/{args.env} "
            f"(kept {result.kept})."
        )
        for name in result.removed:
            print(f"  removed: {name}")
    return 0


def cmd_prune_age(args: argparse.Namespace) -> int:
    result = prune_by_age(
        stack_name=args.stack,
        environment=args.env,
        max_age_days=args.days,
        snapshot_dir=args.snapshot_dir,
    )
    if result.removed_count == 0:
        print(
            f"No snapshots older than {args.days} day(s) for {args.stack}/{args.env} "
            f"(kept {result.kept})."
        )
    else:
        print(
            f"Pruned {result.removed_count} snapshot(s) older than {args.days} day(s) "
            f"for {args.stack}/{args.env} (kept {result.kept})."
        )
        for name in result.removed:
            print(f"  removed: {name}")
    return 0
