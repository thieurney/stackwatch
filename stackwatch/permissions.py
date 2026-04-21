"""Parse and summarize IAM permissions required by a CloudFormation stack."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IamCapability:
    name: str
    description: str


@dataclass
class PermissionSummary:
    stack_name: str
    iam_capabilities: List[IamCapability] = field(default_factory=list)
    resource_types: List[str] = field(default_factory=list)
    has_iam_resources: bool = False
    warning: Optional[str] = None


_CAPABILITY_DESCRIPTIONS = {
    "CAPABILITY_IAM": "Stack creates or modifies IAM resources.",
    "CAPABILITY_NAMED_IAM": "Stack creates or modifies IAM resources with custom names.",
    "CAPABILITY_AUTO_EXPAND": "Stack uses macros or nested stacks that require auto-expansion.",
}

_IAM_RESOURCE_PREFIXES = (
    "AWS::IAM::",
    "AWS::SSO::",
    "AWS::Organizations::",
)


def parse_permission_summary(
    stack_name: str,
    capabilities: List[str],
    resource_types: List[str],
) -> PermissionSummary:
    iam_caps = [
        IamCapability(name=cap, description=_CAPABILITY_DESCRIPTIONS.get(cap, "Unknown capability."))
        for cap in capabilities
    ]
    has_iam = any(
        rt.startswith(_IAM_RESOURCE_PREFIXES) for rt in resource_types
    )
    warning: Optional[str] = None
    if has_iam and not capabilities:
        warning = "Stack contains IAM resources but declares no IAM capabilities."
    return PermissionSummary(
        stack_name=stack_name,
        iam_capabilities=iam_caps,
        resource_types=resource_types,
        has_iam_resources=has_iam,
        warning=warning,
    )


def format_permission_summary(summary: PermissionSummary, *, use_color: bool = True, as_json: bool = False) -> str:
    import json

    if as_json:
        return json.dumps(
            {
                "stack": summary.stack_name,
                "iam_capabilities": [{"name": c.name, "description": c.description} for c in summary.iam_capabilities],
                "resource_types": summary.resource_types,
                "has_iam_resources": summary.has_iam_resources,
                "warning": summary.warning,
            },
            indent=2,
        )

    lines = [f"Stack: {summary.stack_name}"]
    if summary.iam_capabilities:
        lines.append("IAM Capabilities:")
        for cap in summary.iam_capabilities:
            lines.append(f"  {cap.name}: {cap.description}")
    else:
        lines.append("IAM Capabilities: none")
    lines.append(f"IAM Resources Present: {'yes' if summary.has_iam_resources else 'no'}")
    if summary.warning:
        prefix = "\033[33mWARNING\033[0m" if use_color else "WARNING"
        lines.append(f"{prefix}: {summary.warning}")
    return "\n".join(lines)
