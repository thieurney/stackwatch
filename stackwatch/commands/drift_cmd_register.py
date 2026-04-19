"""Registration helper so cli.py can import a single symbol per command module."""
from stackwatch.commands.drift_cmd import add_drift_subcommand

__all__ = ["add_drift_subcommand"]
