"""Registration module for the outputs subcommand.

This module re-exports the outputs subcommand registration function,
providing a consistent interface for command registration across the
stackwatch CLI.
"""

from stackwatch.commands.outputs_cmd import add_outputs_subcommand

__all__ = ["add_outputs_subcommand"]
