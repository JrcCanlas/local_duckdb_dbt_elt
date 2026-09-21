from pathlib import Path
from datetime import datetime
import hashlib, re
import pandas as pd

SAFE_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def file_hash(path: Path):
    """Return a SHA-256 fingerprint for a source file."""

    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_file(path: Path, excel_config=None):
    """Load a supported CSV or Excel file as a string-valued DataFrame."""
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        excel_config = excel_config or {}
        return pd.read_excel(
            path,
            sheet_name=excel_config.get("sheet_name"),
            header=excel_config.get("header", 0),
            dtype=str,
            engine="openpyxl",
        ).fillna("")
    raise ValueError(f"Unsupported file: {path}")
