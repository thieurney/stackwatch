"""Command to validate a CloudFormation template body or URL."""
from __future__ import annotations

import json
from argparse import ArgumentParser, Namespace
from typing import Any

import boto3
from botocore.exceptions import ClientError


def add_validate_subcommand(subparsers: Any) -> None:
    p: ArgumentParser = subparsers.add_parser(
        "validate",
        help="Validate a CloudFormation template",
    )
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", metavar="PATH", help="Local template file to validate")
    source.add_argument("--url", metavar="URL", help="S3 URL of the template to validate")
    p.add_argument("--json", dest="output_json", action="store_true", help="Output as JSON")
    p.add_argument("--profile", default=None, help="AWS profile name")
    p.add_argument("--region", default=None, help="AWS region")
    p.set_defaults(func=cmd_validate)


def _fetch_template_body(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _validate(session: Any, *, body: str | None = None, url: str | None = None) -> dict:
    cf = session.client("cloudformation")
    kwargs: dict = {}
    if body is not None:
        kwargs["TemplateBody"] = body
    else:
        kwargs["TemplateURL"] = url
    return cf.validate_template(**kwargs)


def cmd_validate(args: Namespace) -> int:
    session = boto3.Session(
        profile_name=args.profile,
        region_name=getattr(args, "region", None),
    )

    try:
        if args.file:
            body = _fetch_template_body(args.file)
            result = _validate(session, body=body)
        else:
            result = _validate(session, url=args.url)
    except FileNotFoundError as exc:
        print(f"error: {exc}")
        return 1
    except ClientError as exc:
        print(f"validation failed: {exc.response['Error']['Message']}")
        return 1

    if args.output_json:
        out = {
            "capabilities": result.get("Capabilities", []),
            "capabilities_reason": result.get("CapabilitiesReason", ""),
            "description": result.get("Description", ""),
            "parameters": [
                {"key": p["ParameterKey"], "default": p.get("DefaultValue", "")}
                for p in result.get("Parameters", [])
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print("Template is valid.")
        caps = result.get("Capabilities", [])
        if caps:
            print(f"  Capabilities : {', '.join(caps)}")
            reason = result.get("CapabilitiesReason", "")
            if reason:
                print(f"  Reason       : {reason}")
        desc = result.get("Description", "")
        if desc:
            print(f"  Description  : {desc}")
        params = result.get("Parameters", [])
        if params:
            print(f"  Parameters   : {len(params)} declared")
            for p in params:
                default = p.get("DefaultValue", "(none)")
                print(f"    - {p['ParameterKey']}  default={default}")

    return 0
