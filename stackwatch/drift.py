"""Utilities for parsing and summarising CloudFormation drift detection results."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ResourceDrift:
    logical_id: str
    resource_type: str
    drift_status: str  # MODIFIED | DELETED | NOT_CHECKED
    differences: List[str] = field(default_factory=list)


@dataclass
class DriftSummary:
    stack_name: str
    drift_status: Optional[str]  # DRIFTED | IN_SYNC | NOT_CHECKED | UNKNOWN
    drifted_count: int = 0
    resources: List[ResourceDrift] = field(default_factory=list)

    @property
    def is_drifted(self) -> bool:
        return self.drift_status == "DRIFTED"


def parse_drift_summary(stack_name: str, raw: dict) -> DriftSummary:
    """Build a DriftSummary from a boto3 describe_stack_resource_drifts response."""
    resources: List[ResourceDrift] = []
    for item in raw.get("StackResourceDrifts", []):
        diffs = [
            d.get("PropertyPath", "")
            for d in item.get("PropertyDifferences", [])
        ]
        resources.append(
            ResourceDrift(
                logical_id=item.get("LogicalResourceId", ""),
                resource_type=item.get("ResourceType", ""),
                drift_status=item.get("StackResourceDriftStatus", "NOT_CHECKED"),
                differences=diffs,
            )
        )

    drifted = [r for r in resources if r.drift_status in ("MODIFIED", "DELETED")]
    overall = "DRIFTED" if drifted else ("IN_SYNC" if resources else "NOT_CHECKED")

    return DriftSummary(
        stack_name=stack_name,
        drift_status=overall,
        drifted_count=len(drifted),
        resources=resources,
    )


def format_drift_summary(summary: DriftSummary) -> List[str]:
    """Return a list of human-readable lines describing the drift summary."""
    lines = [
        f"Stack  : {summary.stack_name}",
        f"Status : {summary.drift_status or 'UNKNOWN'}",
        f"Drifted: {summary.drifted_count} resource(s)",
    ]
    for r in summary.resources:
        if r.drift_status in ("MODIFIED", "DELETED"):
            lines.append(f"  [{r.drift_status}] {r.logical_id} ({r.resource_type})")
            for diff in r.differences:
                lines.append(f"    ~ {diff}")
    return lines
