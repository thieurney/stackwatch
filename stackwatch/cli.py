"""CLI entry point for stackwatch."""

import argparse
import sys

import boto3

from stackwatch.fetcher import fetch_stack
from stackwatch.differ import diff_stacks
from stackwatch.formatter import format_stack_diff, format_no_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stackwatch",
        description="Monitor and diff CloudFormation stack states across environments.",
    )
    parser.add_argument("stack_name", help="Name of the CloudFormation stack")
    parser.add_argument("--env-a", required=True, help="First AWS profile/region label")
    parser.add_argument("--env-b", required=True, help="Second AWS profile/region label")
    parser.add_argument(
        "--profile-a", default=None, help="AWS profile for env-a (default: default)"
    )
    parser.add_argument(
        "--profile-b", default=None, help="AWS profile for env-b (default: default)"
    )
    parser.add_argument(
        "--region-a", default="us-east-1", help="AWS region for env-a"
    )
    parser.add_argument(
        "--region-b", default="us-east-1", help="AWS region for env-b"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    use_color = not args.no_color

    session_a = boto3.Session(profile_name=args.profile_a, region_name=args.region_a)
    session_b = boto3.Session(profile_name=args.profile_b, region_name=args.region_b)

    cf_a = session_a.client("cloudformation")
    cf_b = session_b.client("cloudformation")

    state_a = fetch_stack(cf_a, args.stack_name)
    state_b = fetch_stack(cf_b, args.stack_name)

    if state_a is None:
        print(format_no_data(args.stack_name, args.env_a, use_color))
        return 1
    if state_b is None:
        print(format_no_data(args.stack_name, args.env_b, use_color))
        return 1

    diff = diff_stacks(state_a, state_b)
    print(format_stack_diff(diff, args.stack_name, args.env_a, args.env_b, use_color))
    return 0 if not any([diff.status, diff.parameters, diff.outputs]) else 1


if __name__ == "__main__":
    sys.exit(main())
