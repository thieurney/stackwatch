"""Data model and helpers for stack protection state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProtectionReport:
    stack_name: str
    termination_protection: bool
    stack_status: str
    warnings: List[str] = field(default_factory=list)

    @property
    def is_protected(self) -> bool:
        return self.termination_protection


def build_protection_report(
    stack_name: str,
    termination_protection: bool,
    stack_status: str,
) -> ProtectionReport:
    warnings: List[str] = []
    if not termination_protection:
        warnings.append("Termination protection is DISABLED — stack can be deleted without confirmation.")
    delete_statuses = {"DELETE_IN_PROGRESS", "DELETE_FAILED", "DELETE_COMPLETE"}
    if stack_status in delete_statuses:
        warnings.append(f"Stack is in a deletion-related status: {stack_status}")
    return ProtectionReport(
        stack_name=stack_name,
        termination_protection=termination_protection,
        stack_status=stack_status,
        warnings=warnings,
    )


def format_protection_report(report: ProtectionReport, *, color: bool = True) -> str:
    GREEN = "\033[32m" if color else ""
    RED = "\033[31m" if color else ""
    RESET = "\033[0m" if color else ""

    tp_str = f"{GREEN}enabled{RESET}" if report.termination_protection else f"{RED}disabled{RESET}"
    lines = [
        f"Stack:                  {report.stack_name}",
        f"Status:                 {report.stack_status}",
        f"Termination protection: {tp_str}",
    ]
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"  ! {w}")
    return "\n".join(lines)
