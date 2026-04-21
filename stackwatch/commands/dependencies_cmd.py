from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import boto3


@dataclass
class StackDependency:
    stack_name: str
    stack_id: str
    status: str
    nested: bool


def _fetch_dependencies(session: Any, stack_name: str) -> list[StackDependency]:
    """Return stacks that import exports from *stack_name* or are nested within it."""
    cf = session.client("cloudformation")
    deps: list[StackDependency] = []

    # Nested stacks: describe the parent and look for nested resource types
    try:
        paginator = cf.get_paginator("list_stack_resources")
        for page in paginator.paginate(StackName=stack_name):
            for r in page.get("StackResourceSummaries", []):
                if r["ResourceType"] == "AWS::CloudFormation::Stack":
                    nested_id = r.get("PhysicalResourceId", "")
                    nested_name = nested_id.split("/")[1] if "/" in nested_id else nested_id
                    deps.append(
                        StackDependency(
                            stack_name=nested_name,
                            stack_id=nested_id,
                            status=r.get("ResourceStatus", "UNKNOWN"),
                            nested=True,
                        )
                    )
    except cf.exceptions.ValidationError:
        pass

    # Cross-stack references: list imports of each export from this stack
    try:
        exports_paginator = cf.get_paginator("list_exports")
        stack_exports: list[str] = []
        for page in exports_paginator.paginate():
            for exp in page.get("Exports", []):
                if exp.get("ExportingStackId", "").split("/")[1] == stack_name or \
                   exp.get("ExportingStackId", "") == stack_name:
                    stack_exports.append(exp["Name"])

        seen: set[str] = {d.stack_name for d in deps}
        for export_name in stack_exports:
            try:
                imports_paginator = cf.get_paginator("list_imports")
                for page in imports_paginator.paginate(ExportName=export_name):
                    for importing_stack in page.get("Imports", []):
                        if importing_stack not in seen:
                            seen.add(importing_stack)
                            deps.append(
                                StackDependency(
                                    stack_name=importing_stack,
                                    stack_id=importing_stack,
                                    status="IMPORTING",
                                    nested=False,
                                )
                            )
            except cf.exceptions.CFNRegistryException:
                pass
    except Exception:
        pass

    return deps


def add_dependencies_subcommand(subparsers: Any) -> None:
    p = subparsers.add_parser("dependencies", help="Show stacks that depend on this stack")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.set_defaults(func=cmd_dependencies)


def cmd_dependencies(args: Any) -> int:
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    deps = _fetch_dependencies(session, args.stack)

    if not deps:
        print(f"No dependencies found for stack '{args.stack}'.")
        return 0

    if args.as_json:
        print(json.dumps([{"stack_name": d.stack_name, "stack_id": d.stack_id,
                           "status": d.status, "nested": d.nested} for d in deps], indent=2))
        return 0

    print(f"Dependencies of '{args.stack}':")
    for d in deps:
        kind = "nested" if d.nested else "import"
        print(f"  [{kind}] {d.stack_name}  ({d.status})")
    return 0
