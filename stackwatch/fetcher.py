"""Fetch CloudFormation stack state from AWS."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StackState:
    name: str
    status: str
    parameters: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)


def fetch_stack(
    stack_name: str,
    env: str = "default",
    region: Optional[str] = None,
) -> Optional[StackState]:
    """Fetch a CloudFormation stack and return its state.

    Returns None if the stack does not exist.
    """
    try:
        import boto3
        session = boto3.Session(profile_name=env if env != "default" else None,
                                region_name=region)
        cf = session.client("cloudformation")
        resp = cf.describe_stacks(StackName=stack_name)
        stacks = resp.get("Stacks", [])
        if not stacks:
            return None
        s = stacks[0]

        parameters = {
            p["ParameterKey"]: p.get("ParameterValue", "")
            for p in s.get("Parameters", [])
        }
        outputs = {
            o["OutputKey"]: o.get("OutputValue", "")
            for o in s.get("Outputs", [])
        }
        tags = {
            t["Key"]: t["Value"]
            for t in s.get("Tags", [])
        }
        return StackState(
            name=stack_name,
            status=s["StackStatus"],
            parameters=parameters,
            outputs=outputs,
            tags=tags,
            raw=s,
        )
    except Exception:
        return None
