"""Utilities for loading YAML configuration used by the ETL application."""

from pathlib import Path
import yaml


def read_yaml(path: Path) -> dict:
    """Load a YAML file from disk and return its parsed contents.

    Args:
        path: Path to the YAML file to read.

    Returns:
        dict: A Python dictionary generated from the YAML document. Empty or
        whitespace-only YAML files return an empty dictionary instead of None.
    """
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
