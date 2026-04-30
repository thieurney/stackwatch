"""CLI command: stackwatch budgets — show budget alerts for a stack."""
from __future__ import annotations

import json
import argparse
from typing import Any

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.budgets import build_budget_report, format_budget_report


def _fetch_raw_budgets(session: Any, account_id: str, stack_name: str) -> list[dict]:
    client = session.client("budgets")
    paginator = client.get_paginator("describe_budgets")
    results = []
    for page in paginator.paginate(AccountId=account_id):
        for budget in page.get("Budgets", []):
            name: str = budget.get("BudgetName", "")
            if stack_name.lower() in name.lower():
                results.append(budget)
    return results


def add_budgets_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("budgets", help="Show AWS budget alerts related to a stack")
    p.add_argument("stack", help="CloudFormation stack name")
    p.add_argument("--region", default=None)
    p.add_argument("--profile", default=None)
    p.add_argument("--account-id", required=True, dest="account_id",
                   help="AWS account ID for Budgets API")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(func=cmd_budgets)


def cmd_budgets(args: argparse.Namespace) -> int:
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    state = fetch_stack(session, args.stack)
    if state is None:
        print(f"Stack '{args.stack}' not found.")
        return 1

    raw = _fetch_raw_budgets(session, args.account_id, args.stack)
    report = build_budget_report(args.stack, raw)

    if args.as_json:
        payload = {
            "stack": report.stack_name,
            "exceeded_count": report.exceeded_count,
            "alerts": [
                {
                    "name": a.name,
                    "limit_amount": a.limit_amount,
                    "limit_unit": a.limit_unit,
                    "actual_spend": a.actual_spend,
                    "forecasted_spend": a.forecasted_spend,
                    "exceeded": a.exceeded,
                    "pct_used": a.pct_used,
                }
                for a in report.alerts
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_budget_report(report, color=not args.no_color))

    return 1 if report.has_exceeded else 0
