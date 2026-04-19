"""Command for filtering and displaying stack resources by tag."""
from __future__ import annotations

import argparse
from typing import Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import format_no_data


def add_tag_subcommand(subparsers) -> None:
    p = subparsers.add_parser("tags", help="Show or filter stacks by tag")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--env", default="default", help="AWS profile / environment")
    p.add_argument("--filter", dest="tag_filter", metavar="KEY=VALUE",
                   help="Only show stacks where tag KEY equals VALUE")
    p.add_argument("--region", default=None, help="AWS region")
    p.set_defaults(func=cmd_tags)


def _parse_tag_filter(raw: Optional[str]) -> Optional[tuple[str, str]]:
    if raw is None:
        return None
    if "=" not in raw:
        raise ValueError(f"Invalid tag filter '{raw}': expected KEY=VALUE")
    key, _, value = raw.partition("=")
    return key.strip(), value.strip()


def cmd_tags(args: argparse.Namespace, out=None) -> int:
    import sys
    if out is None:
        out = sys.stdout

    try:
        tag_filter = _parse_tag_filter(getattr(args, "tag_filter", None))
    except ValueError as exc:
        print(f"Error: {exc}", file=out)
        return 1

    state = fetch_stack(args.stack, env=args.env, region=args.region)
    if state is None:
        print(format_no_data(args.stack), file=out)
        return 1

    tags: dict = state.tags if state.tags else {}

    if tag_filter is not None:
        key, value = tag_filter
        if tags.get(key) != value:
            print(f"Stack '{args.stack}' does not match tag {key}={value}", file=out)
            return 1
        print(f"Stack '{args.stack}' matches tag {key}={value}", file=out)
        return 0

    if not tags:
        print(f"Stack '{args.stack}' has no tags.", file=out)
        return 0

    print(f"Tags for stack '{args.stack}':", file=out)
    for k, v in sorted(tags.items()):
        print(f"  {k} = {v}", file=out)
    return 0
