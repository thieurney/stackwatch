import json
from argparse import _SubParsersAction
from typing import Optional

from stackwatch.fetcher import fetch_stack
from stackwatch.formatter import format_no_data


def add_drift_subcommand(subparsers: _SubParsersAction) -> None:
    p = subparsers.add_parser("drift", help="Show CloudFormation drift status for a stack")
    p.add_argument("stack", help="Stack name")
    p.add_argument("--region", default=None, help="AWS region")
    p.add_argument("--profile", default=None, help="AWS profile")
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.add_argument("--no-color", action="store_true", help="Disable color output")
    p.set_defaults(func=cmd_drift)


def _format_drift_status(status: Optional[str], no_color: bool) -> str:
    if status is None:
        return "UNKNOWN"
    colors = {
        "DRIFTED": "\033[31m",
        "IN_SYNC": "\033[32m",
        "NOT_CHECKED": "\033[33m",
    }
    reset = "\033[0m"
    if no_color or status not in colors:
        return status
    return f"{colors[status]}{status}{reset}"


def cmd_drift(args, out=None, err=None) -> int:
    import sys
    out = out or sys.stdout
    err = err or sys.stderr

    state = fetch_stack(args.stack, region=args.region, profile=args.profile)
    if state is None:
        print(format_no_data(args.stack), file=err)
        return 1

    drift_status = getattr(state, "drift_status", None)
    drifted_resources = getattr(state, "drifted_resources", [])

    if args.as_json:
        payload = {
            "stack": args.stack,
            "drift_status": drift_status,
            "drifted_resources": drifted_resources,
        }
        print(json.dumps(payload, indent=2), file=out)
        return 0

    label = _format_drift_status(drift_status, args.no_color)
    print(f"Stack : {args.stack}", file=out)
    print(f"Drift : {label}", file=out)
    if drifted_resources:
        print("Drifted resources:", file=out)
        for r in drifted_resources:
            print(f"  - {r}", file=out)
    return 0
