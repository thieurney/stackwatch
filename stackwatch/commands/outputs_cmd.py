"""CLI subcommand: outputs — show and diff stack outputs."""
from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from typing import Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import _color, format_no_data
from stackwatch.outputs import OutputDiff, diff_outputs, parse_outputs
from stackwatch.snapshot import load_snapshot


def add_outputs_subcommand(sub) -> None:
    p: ArgumentParser = sub.add_parser("outputs", help="Show or diff stack outputs")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--profile", default=None)
    p.add_argument("--region", default=None)
    p.add_argument("--diff-snapshot", metavar="LABEL",
                   help="Compare current outputs against a saved snapshot")
    p.add_argument("--snapshot-dir", default=".stackwatch")
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="Output as JSON")
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(func=cmd_outputs)


def _format_diff(d: OutputDiff, color: bool) -> str:
    old = d.old_value if d.old_value is not None else "(none)"
    new = d.new_value if d.new_value is not None else "(none)"
    line = f"  {d.key}: {old} -> {new}"
    if color:
        line = _color(line, "yellow")
    return line


def cmd_outputs(args: Namespace) -> int:
    state = fetch_stack(args.stack, profile=args.profile, region=args.region)
    if state is None:
        print(format_no_data(args.stack))
        return 1

    use_color = not args.no_color

    if args.diff_snapshot:
        snapshot = load_snapshot(args.stack, args.diff_snapshot,
                                 directory=args.snapshot_dir)
        if snapshot is None:
            print(f"Snapshot '{args.diff_snapshot}' not found for stack '{args.stack}'.")
            return 1
        diffs = diff_outputs(snapshot, state)
        if args.as_json:
            print(json.dumps(
                [{"key": d.key, "old": d.old_value, "new": d.new_value} for d in diffs],
                indent=2,
            ))
        elif not diffs:
            print("No output changes since snapshot.")
        else:
            print(f"Output changes vs snapshot '{args.diff_snapshot}':")
            for d in diffs:
                print(_format_diff(d, use_color))
        return 0

    outputs = parse_outputs(state)
    if args.as_json:
        print(json.dumps(
            [{"key": o.key, "value": o.value,
              "description": o.description, "export": o.export_name}
             for o in outputs],
            indent=2,
        ))
    elif not outputs:
        print(f"Stack '{args.stack}' has no outputs.")
    else:
        print(f"Outputs for {args.stack}:")
        for o in outputs:
            desc = f"  # {o.description}" if o.description else ""
            print(f"  {o.key} = {o.value}{desc}")
    return 0
