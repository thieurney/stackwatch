"""Command to fetch and display the CloudFormation template for a stack."""

import json
import sys
from argparse import ArgumentParser, Namespace
from typing import IO, Optional

import boto3
import yaml


def add_template_subcommand(subparsers) -> None:
    """Register the 'template' subcommand with the given subparser group."""
    parser: ArgumentParser = subparsers.add_parser(
        "template",
        help="Fetch and display the CloudFormation template for a stack.",
    )
    parser.add_argument("stack", help="Name or ARN of the CloudFormation stack.")
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region (defaults to the current profile region).",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS CLI profile to use.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "raw"],
        default="raw",
        help=(
            "Output format.  'raw' prints the template exactly as returned by AWS; "
            "'json' and 'yaml' re-serialise it (default: raw)."
        ),
    )
    parser.add_argument(
        "--stage",
        choices=["Original", "Processed"],
        default="Original",
        help="Template stage to retrieve (default: Original).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    parser.set_defaults(func=cmd_template)


def _fetch_template(stack_name: str, stage: str, region: Optional[str], profile: Optional[str]) -> Optional[str]:
    """Return the raw template body string, or None if the stack does not exist."""
    session = boto3.Session(region_name=region, profile_name=profile)
    client = session.client("cloudformation")
    try:
        response = client.get_template(
            StackName=stack_name,
            TemplateStage=stage,
        )
        return response.get("TemplateBody", "")
    except client.exceptions.ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("ValidationError", "StackNotFoundException"):
            return None
        raise


def _reformat(raw: str, fmt: str) -> str:
    """Re-serialise *raw* template body into the requested format.

    AWS may return the body as a string (JSON or YAML) or, for processed
    templates, occasionally as a dict.  We handle both.
    """
    if fmt == "raw":
        return raw if isinstance(raw, str) else json.dumps(raw, indent=2)

    # Parse the body into a Python dict regardless of its original format.
    if isinstance(raw, dict):
        data = raw
    else:
        raw_str: str = raw
        try:
            data = json.loads(raw_str)
        except (json.JSONDecodeError, ValueError):
            # Fall back to YAML (CloudFormation templates may be YAML).
            data = yaml.safe_load(raw_str)

    if fmt == "json":
        return json.dumps(data, indent=2)
    # fmt == "yaml"
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def cmd_template(args: Namespace, out: IO[str] = sys.stdout) -> int:
    """Entry point for the 'template' subcommand.

    Returns 0 on success, 1 when the stack cannot be found.
    """
    raw = _fetch_template(
        stack_name=args.stack,
        stage=args.stage,
        region=getattr(args, "region", None),
        profile=getattr(args, "profile", None),
    )

    if raw is None:
        print(f"Stack '{args.stack}' not found.", file=sys.stderr)
        return 1

    formatted = _reformat(raw, args.format)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(formatted)
                if not formatted.endswith("\n"):
                    fh.write("\n")
            print(f"Template written to {args.output}", file=out)
        except OSError as exc:
            print(f"Error writing to {args.output}: {exc}", file=sys.stderr)
            return 1
    else:
        print(formatted, file=out)

    return 0
