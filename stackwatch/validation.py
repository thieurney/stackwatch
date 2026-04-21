"""Helpers for parsing and representing CloudFormation template validation results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateParameter:
    key: str
    default_value: str = ""
    no_echo: bool = False


@dataclass
class ValidationResult:
    valid: bool
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    capabilities_reason: str = ""
    parameters: list[TemplateParameter] = field(default_factory=list)
    error_message: str = ""


def parse_validation_response(response: dict[str, Any]) -> ValidationResult:
    """Convert a raw boto3 validate_template response into a ValidationResult."""
    params = [
        TemplateParameter(
            key=p["ParameterKey"],
            default_value=p.get("DefaultValue", ""),
            no_echo=p.get("NoEcho", False),
        )
        for p in response.get("Parameters", [])
    ]
    return ValidationResult(
        valid=True,
        description=response.get("Description", ""),
        capabilities=response.get("Capabilities", []),
        capabilities_reason=response.get("CapabilitiesReason", ""),
        parameters=params,
    )


def format_validation_result(result: ValidationResult, *, color: bool = True) -> str:
    """Return a human-readable string for a ValidationResult."""
    if not result.valid:
        msg = result.error_message or "unknown error"
        prefix = "\033[31m✗\033[0m" if color else "✗"
        return f"{prefix} Validation failed: {msg}"

    prefix = "\033[32m✓\033[0m" if color else "✓"
    lines = [f"{prefix} Template is valid."]
    if result.description:
        lines.append(f"  Description  : {result.description}")
    if result.capabilities:
        lines.append(f"  Capabilities : {', '.join(result.capabilities)}")
        if result.capabilities_reason:
            lines.append(f"  Reason       : {result.capabilities_reason}")
    if result.parameters:
        lines.append(f"  Parameters   : {len(result.parameters)} declared")
        for p in result.parameters:
            echo_tag = " [NoEcho]" if p.no_echo else ""
            default = p.default_value or "(none)"
            lines.append(f"    - {p.key}  default={default}{echo_tag}")
    return "\n".join(lines)
