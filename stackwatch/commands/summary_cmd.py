"""summary_cmd.py — show a high-level summary of a CloudFormation stack."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional

from stackwatch.fetcher import StackState, fetch_stack
from stackwatch.drift import parse_drift_summary, is_drifted
from stackwatch.protection import build_protection_report


@dataclass
class StackSummary:
    """Aggregated high-level summary of a single stack."""

    stack_name: str
    status: str
    region: str
    description: Optional[str]
    parameter_count: int
    output_count: int
    resource_count_hint: str  # from stack metadata, not a full resource list call
    drift_status: str
    termination_protected: bool
    capabilities: list[str]
    tags: dict[str, str]


def _build_summary(state: StackState) -> StackSummary:
    """Derive a StackSummary from a StackState."""
    raw = state.raw or {}

    drift_summary = parse_drift_summary(raw)
    protection_report = build_protection_report(state)

    tags: dict[str, str] = {}
    for entry in raw.get("Tags", []):
        tags[entry.get("Key", "")] = entry.get("Value", "")

    return StackSummary(
        stack_name=state.stack_name,
        status=state.status,
        region=state.region,
        description=raw.get("Description"),
        parameter_count=len(state.parameters),
        output_count=len(raw.get("Outputs", [])),
        resource_count_hint=str(raw.get("DeclaredTransforms", "n/a")),
        drift_status=drift_summary.drift_status,
        termination_protected=protection_report.termination_protection_enabled,
        capabilities=raw.get("Capabilities", []),
        tags=tags,
    )


def _format_summary_plain(summary: StackSummary, *, color: bool = True) -> str:
    """Render the summary as a human-readable block of text."""
    lines: list[str] = []

    def row(label: str, value: object) -> None:
        lines.append(f"  {label:<28} {value}")

    lines.append(f"Stack: {summary.stack_name}  [{summary.region}]")
    lines.append("-" * 50)
    row("Status", summary.status)
    if summary.description:
        row("Description", summary.description)
    row("Parameters", summary.parameter_count)
    row("Outputs", summary.output_count)
    row("Drift status", summary.drift_status)
    row("Termination protection", "enabled" if summary.termination_protected else "disabled")
    if summary.capabilities:
        row("Capabilities", ", ".join(summary.capabilities))
    if summary.tags:
        row("Tags", len(summary.tags))
        for k, v in summary.tags.items():
            lines.append(f"    {k} = {v}")
    return "\n".join(lines)


def add_summary_subcommand(subparsers) -> None:  # type: ignore[type-arg]
    """Register the 'summary' subcommand on *subparsers*."""
    p = subparsers.add_parser(
        "summary",
        help="Show a high-level summary of a stack",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Emit JSON output",
    )
    p.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        help="Disable ANSI colour codes",
    )
    p.set_defaults(func=cmd_summary)


def cmd_summary(args, session) -> int:  # type: ignore[type-arg]
    """Entry point for the 'summary' subcommand."""
    state: Optional[StackState] = fetch_stack(
        session, args.stack, region=args.region
    )

    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    summary = _build_summary(state)

    if args.output_json:
        print(json.dumps(asdict(summary), indent=2, default=str))
    else:
        print(_format_summary_plain(summary, color=not args.no_color))

    return 0
