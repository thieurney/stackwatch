from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from typing import Optional

from stackwatch.fetcher import StackState, fetch_stack


def add_params_subcommand(sub) -> None:
    p: ArgumentParser = sub.add_parser(
        "params",
        help="Show or diff parameters for a CloudFormation stack",
    )
    p.add_argument("stack", help="Stack name or ARN")
    p.add_argument("--env", default="default", help="Environment label")
    p.add_argument(
        "--compare-env",
        dest="compare_env",
        default=None,
        help="Second environment to diff parameters against",
    )
    p.add_argument(
        "--filter",
        dest="key_filter",
        default=None,
        help="Only show parameters whose key contains this substring",
    )
    p.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON")
    p.set_defaults(func=cmd_params)


def _filter_params(
    params: dict[str, str], key_filter: Optional[str]
) -> dict[str, str]:
    if not key_filter:
        return params
    return {k: v for k, v in params.items() if key_filter.lower() in k.lower()}


def _params_as_dict(state: StackState) -> dict[str, str]:
    return {p["ParameterKey"]: p.get("ParameterValue", "") for p in (state.parameters or [])}


def cmd_params(args: Namespace, boto_session) -> int:
    state: Optional[StackState] = fetch_stack(args.stack, args.env, boto_session)
    if state is None:
        print(f"Stack '{args.stack}' not found in env '{args.env}'.")
        return 1

    params = _filter_params(_params_as_dict(state), args.key_filter)

    if args.compare_env is None:
        # Plain display
        if not params:
            print("No parameters found.")
            return 0
        if args.as_json:
            print(json.dumps(params, indent=2))
        else:
            for k, v in sorted(params.items()):
                print(f"  {k}: {v}")
        return 0

    # Diff mode
    other: Optional[StackState] = fetch_stack(args.stack, args.compare_env, boto_session)
    if other is None:
        print(f"Stack '{args.stack}' not found in env '{args.compare_env}'.")
        return 1

    other_params = _filter_params(_params_as_dict(other), args.key_filter)
    diff = _build_param_diff(params, other_params)

    if not diff:
        print("Parameters are identical across environments.")
        return 0

    if args.as_json:
        print(json.dumps(diff, indent=2))
    else:
        for k, entry in sorted(diff.items()):
            old = entry.get("old", "<missing>")
            new = entry.get("new", "<missing>")
            print(f"  {k}: {old!r} -> {new!r}")
    return 0


def _build_param_diff(
    left: dict[str, str], right: dict[str, str]
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    all_keys = set(left) | set(right)
    for k in all_keys:
        lv = left.get(k)
        rv = right.get(k)
        if lv != rv:
            entry: dict = {}
            if lv is not None:
                entry["old"] = lv
            if rv is not None:
                entry["new"] = rv
            result[k] = entry
    return result
