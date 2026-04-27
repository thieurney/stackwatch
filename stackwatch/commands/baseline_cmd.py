"""CLI sub-commands for baseline management (save / diff / list)."""
from __future__ import annotations

import argparse
import sys
from typing import List

from stackwatch.fetcher import fetch_stack
from stackwatch.snapshot import save_snapshot, load_snapshot, list_snapshots
from stackwatch.baseline import (
    build_baseline_report,
    drifted_from_baseline,
    format_baseline_report,
)


def _dir_kwargs(args: argparse.Namespace) -> dict:
    kwargs: dict = {}
    if hasattr(args, "snapshot_dir") and args.snapshot_dir:
        kwargs["snapshot_dir"] = args.snapshot_dir
    return kwargs


def add_baseline_subcommands(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("baseline", help="Manage stack baselines")
    bs = p.add_subparsers(dest="baseline_cmd", required=True)

    # save
    save_p = bs.add_parser("save", help="Save current state as a named baseline")
    save_p.add_argument("stack", help="Stack name")
    save_p.add_argument("label", help="Baseline label (e.g. 'prod-v1.2')")
    save_p.add_argument("--region", default=None)
    save_p.add_argument("--profile", default=None)
    save_p.add_argument("--snapshot-dir", default=None)
    save_p.set_defaults(func=cmd_baseline_save)

    # diff
    diff_p = bs.add_parser("diff", help="Diff current state against a saved baseline")
    diff_p.add_argument("stack", help="Stack name")
    diff_p.add_argument("label", help="Baseline label to compare against")
    diff_p.add_argument("--region", default=None)
    diff_p.add_argument("--profile", default=None)
    diff_p.add_argument("--snapshot-dir", default=None)
    diff_p.add_argument("--no-color", action="store_true", default=False)
    diff_p.set_defaults(func=cmd_baseline_diff)

    # list
    list_p = bs.add_parser("list", help="List saved baselines for a stack")
    list_p.add_argument("stack", help="Stack name")
    list_p.add_argument("--snapshot-dir", default=None)
    list_p.set_defaults(func=cmd_baseline_list)


def cmd_baseline_save(args: argparse.Namespace) -> int:
    import boto3

    session = boto3.Session(
        region_name=getattr(args, "region", None),
        profile_name=getattr(args, "profile", None),
    )
    state = fetch_stack(args.stack, session)
    if state is None:
        print(f"error: stack '{args.stack}' not found", file=sys.stderr)
        return 1
    path = save_snapshot(args.stack, state, label=args.label, **_dir_kwargs(args))
    print(f"Baseline '{args.label}' saved → {path}")
    return 0


def cmd_baseline_diff(args: argparse.Namespace) -> int:
    import boto3

    session = boto3.Session(
        region_name=getattr(args, "region", None),
        profile_name=getattr(args, "profile", None),
    )
    baseline = load_snapshot(args.stack, label=args.label, **_dir_kwargs(args))
    current = fetch_stack(args.stack, session)
    report = build_baseline_report(args.stack, args.label, baseline, current)
    print(format_baseline_report(report, color=not args.no_color))
    return 1 if drifted_from_baseline(report) else 0


def cmd_baseline_list(args: argparse.Namespace) -> int:
    snapshots: List[str] = list_snapshots(args.stack, **_dir_kwargs(args))
    if not snapshots:
        print(f"No baselines found for '{args.stack}'")
        return 0
    for s in snapshots:
        print(s)
    return 0
