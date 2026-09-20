from pathlib import Path
import yaml


def read_yaml(path: Path) -> dict:
    """Read a YAML configuration file and and return an empty mapping if it is empty."""
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
