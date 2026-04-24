"""graph_cmd.py — render a dependency graph of CloudFormation stacks.

Outputs either a plain-text adjacency list or a DOT-format graph suitable
for rendering with Graphviz (``dot -Tpng graph.dot -o graph.png``).
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import boto3


@dataclass
class StackNode:
    """Represents a single stack in the dependency graph."""

    name: str
    status: str
    region: str
    imports: List[str] = field(default_factory=list)   # stacks this one imports from
    exports: List[str] = field(default_factory=list)   # export names this stack publishes


def _fetch_graph(session: boto3.Session, region: str) -> Dict[str, StackNode]:
    """Fetch all stacks and build an export→stack index to resolve edges."""
    cf = session.client("cloudformation", region_name=region)

    # --- collect all stacks ---
    nodes: Dict[str, StackNode] = {}
    paginator = cf.get_paginator("list_stacks")
    active_statuses = [
        "CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE",
        "ROLLBACK_COMPLETE", "IMPORT_COMPLETE", "IMPORT_ROLLBACK_COMPLETE",
    ]
    for page in paginator.paginate(StackStatusFilter=active_statuses):
        for s in page.get("StackSummaries", []):
            name = s["StackName"]
            nodes[name] = StackNode(
                name=name,
                status=s["StackStatus"],
                region=region,
            )

    # --- collect exports and build export→owner map ---
    export_owner: Dict[str, str] = {}  # export name → stack name
    exp_paginator = cf.get_paginator("list_exports")
    for page in exp_paginator.paginate():
        for exp in page.get("Exports", []):
            owner = exp["ExportingStackId"].split("/")[1]  # extract stack name
            exp_name = exp["Name"]
            export_owner[exp_name] = owner
            if owner in nodes:
                nodes[owner].exports.append(exp_name)

    # --- resolve imports for each stack ---
    for name in list(nodes.keys()):
        try:
            imp_paginator = cf.get_paginator("list_imports")
            for page in imp_paginator.paginate(ExportName=name):
                for importing_stack in page.get("Imports", []):
                    if importing_stack in nodes:
                        # edge: importing_stack depends on the owner of `name`
                        owner = export_owner.get(name)
                        if owner and owner != importing_stack:
                            nodes[importing_stack].imports.append(owner)
        except cf.exceptions.ClientError:
            pass  # export may not exist or no imports

    return nodes


def _format_dot(nodes: Dict[str, StackNode]) -> str:
    """Render the graph in Graphviz DOT format."""
    lines = ["digraph StackDependencies {", "    rankdir=LR;"]
    for node in nodes.values():
        label = f"{node.name}\\n{node.status}"
        lines.append(f'    "{node.name}" [label="{label}"];')
    edges: set = set()
    for node in nodes.values():
        for dep in node.imports:
            edge = (dep, node.name)
            if edge not in edges:
                edges.add(edge)
                lines.append(f'    "{dep}" -> "{node.name}";')
    lines.append("}")
    return "\n".join(lines)


def _format_plain(nodes: Dict[str, StackNode]) -> str:
    """Render the graph as a human-readable adjacency list."""
    if not nodes:
        return "(no stacks found)"
    lines = []
    for node in sorted(nodes.values(), key=lambda n: n.name):
        deps = ", ".join(sorted(set(node.imports))) or "(none)"
        lines.append(f"{node.name}  [{node.status}]")
        lines.append(f"  depends on: {deps}")
        if node.exports:
            lines.append(f"  exports:    {', '.join(sorted(node.exports))}")
    return "\n".join(lines)


def add_graph_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the ``graph`` sub-command."""
    p = subparsers.add_parser(
        "graph",
        help="render a dependency graph of all stacks in a region",
    )
    p.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    p.add_argument(
        "--format",
        choices=["plain", "dot", "json"],
        default="plain",
        help="output format (default: plain)",
    )
    p.add_argument("--profile", default=None, help="AWS profile name")
    p.set_defaults(func=cmd_graph)


def cmd_graph(args: argparse.Namespace) -> int:
    """Entry point for the ``graph`` command."""
    session = boto3.Session(profile_name=args.profile)
    nodes = _fetch_graph(session, args.region)

    fmt = getattr(args, "format", "plain")
    if fmt == "dot":
        print(_format_dot(nodes))
    elif fmt == "json":
        data = [
            {
                "name": n.name,
                "status": n.status,
                "region": n.region,
                "depends_on": sorted(set(n.imports)),
                "exports": sorted(n.exports),
            }
            for n in sorted(nodes.values(), key=lambda x: x.name)
        ]
        print(json.dumps(data, indent=2))
    else:
        print(_format_plain(nodes))

    return 0
