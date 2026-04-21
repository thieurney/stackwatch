"""Command for displaying AWS account and region context for a stack."""

from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Optional

import boto3

from stackwatch.fetcher import StackState, fetch_stack
from stackwatch.formatter import format_no_data


@dataclass
class AccountContext:
    """AWS account and region context resolved for a given session."""

    account_id: str
    account_alias: Optional[str]
    region: str
    user_arn: Optional[str]


def _fetch_account_context(session: boto3.Session) -> AccountContext:
    """Resolve account ID, alias, region, and caller identity from the session."""
    region = session.region_name or "unknown"

    sts = session.client("sts")
    try:
        identity = sts.get_caller_identity()
        account_id = identity.get("Account", "unknown")
        user_arn = identity.get("Arn")
    except Exception:  # pragma: no cover
        account_id = "unknown"
        user_arn = None

    iam = session.client("iam")
    try:
        aliases = iam.list_account_aliases().get("AccountAliases", [])
        account_alias = aliases[0] if aliases else None
    except Exception:
        account_alias = None

    return AccountContext(
        account_id=account_id,
        account_alias=account_alias,
        region=region,
        user_arn=user_arn,
    )


def _format_context(ctx: AccountContext, state: StackState, *, use_json: bool) -> str:
    """Format account context and stack identity for display."""
    if use_json:
        return json.dumps(
            {
                "stack_name": state.name,
                "stack_id": state.stack_id,
                "account_id": ctx.account_id,
                "account_alias": ctx.account_alias,
                "region": ctx.region,
                "user_arn": ctx.user_arn,
            },
            indent=2,
        )

    lines = [
        f"Stack:          {state.name}",
        f"Stack ID:       {state.stack_id or 'n/a'}",
        f"Account ID:     {ctx.account_id}",
    ]
    if ctx.account_alias:
        lines.append(f"Account Alias:  {ctx.account_alias}")
    lines.append(f"Region:         {ctx.region}")
    if ctx.user_arn:
        lines.append(f"Caller ARN:     {ctx.user_arn}")
    return "\n".join(lines)


def add_accounts_subcommand(subparsers) -> None:  # type: ignore[type-arg]
    """Register the 'accounts' subcommand with the given subparser group."""
    p: ArgumentParser = subparsers.add_parser(
        "account",
        help="Show AWS account and region context for a stack.",
    )
    p.add_argument("stack", help="CloudFormation stack name")
    p.add_argument("--region", help="AWS region override")
    p.add_argument("--profile", help="AWS CLI profile name")
    p.add_argument(
        "--json", dest="use_json", action="store_true", help="Output as JSON"
    )
    p.set_defaults(func=cmd_account)


def cmd_account(args: Namespace) -> int:
    """Entry point for the 'account' subcommand."""
    session = boto3.Session(
        region_name=getattr(args, "region", None),
        profile_name=getattr(args, "profile", None),
    )

    state = fetch_stack(args.stack, session)
    if state is None:
        print(format_no_data(args.stack))
        return 1

    ctx = _fetch_account_context(session)
    print(_format_context(ctx, state, use_json=getattr(args, "use_json", False)))
    return 0
