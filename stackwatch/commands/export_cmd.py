"""Export stack diff or snapshot to JSON/CSV formats."""
from __future__ import annotations

import csv
import json
import sys
from argparse import ArgumentParser, Namespace
from typing import IO

from stackwatch.differ import diff_stacks
from stackwatch.fetcher import fetch_stack
from stackwatch.snapshot import load_snapshot


def add_export_subcommand(subparsers) -> None:
    p: ArgumentParser = subparsers.add_parser(
        "export", help="Export a stack diff to JSON or CSV"
    )
    p.add_argument("stack", help="Stack name")
    p.add_argument("--env-a", default="prod", help="First environment profile")
    p.add_argument("--env-b", default=None, help="Second environment profile (omit to compare with snapshot)")
    p.add_argument("--snapshot", default="baseline", help="Snapshot label when env-b is omitted")
    p.add_argument("--format", choices=["json", "csv"], default="json", dest="fmt")
    p.add_argument("--output", default="-", help="Output file path (default: stdout)")
    p.add_argument("--dir", default=".stackwatch", help="Snapshot directory")
    p.set_defaults(func=cmd_export)


def _open_output(path: str) -> IO[str]:
    if path == "-":
        return sys.stdout
    return open(path, "w", newline="", encoding="utf-8")  # noqa: WPS515


def cmd_export(args: Namespace) -> int:
    if args.env_b:
        state_a = fetch_stack(args.stack, profile=args.env_a)
        state_b = fetch_stack(args.stack, profile=args.env_b)
    else:
        state_a = load_snapshot(args.stack, args.snapshot, directory=args.dir)
        state_b = fetch_stack(args.stack, profile=args.env_a)

    if state_a is None or state_b is None:
        print("error: one or both stack states could not be retrieved", file=sys.stderr)
        return 1

    diff = diff_stacks(state_a, state_b)

    rows = [
        {"field": fd.field, "old": fd.old, "new": fd.new}
        for fd in diff.fields
    ]

    out = _open_output(args.output)
    try:
        if args.fmt == "json":
            json.dump({"stack": diff.stack_name, "changes": rows}, out, indent=2)
            out.write("\n")
        else:
            writer = csv.DictWriter(out, fieldnames=["field", "old", "new"])
            writer.writeheader()
            writer.writerows(rows)
    finally:
        if out is not sys.stdout:
            out.close()

    return 0
