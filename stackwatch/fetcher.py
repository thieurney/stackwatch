"""Fetch CloudFormation stack state from AWS."""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StackState:
    name: str
    status: str
    region: str
    parameters: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)


def fetch_stack(stack_name: str, region: str, profile: Optional[str] = None) -> StackState:
    """Fetch the current state of a CloudFormation stack."""
    session = boto3.Session(region_name=region, profile_name=profile)
    cf = session.client("cloudformation")

    try:
        response = cf.describe_stacks(StackName=stack_name)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ValidationError":
            raise ValueError(f"Stack '{stack_name}' not found in region '{region}'.")
        raise

    stack = response["Stacks"][0]

    parameters = {
        p["ParameterKey"]: p.get("ParameterValue", "")
        for p in stack.get("Parameters", [])
    }
    outputs = {
        o["OutputKey"]: o.get("OutputValue", "")
        for o in stack.get("Outputs", [])
    }
    tags = {
        t["Key"]: t["Value"]
        for t in stack.get("Tags", [])
    }

    return StackState(
        name=stack_name,
        status=stack["StackStatus"],
        region=region,
        parameters=parameters,
        outputs=outputs,
        tags=tags,
    )
