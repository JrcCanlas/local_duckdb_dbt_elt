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


def convert_excel_to_parquet(path, output_path, excel_config=None, data=None):
    """Convert an Excel worksheet to Parquet using an atomic replacement."""
    data = data if data is not None else read_file(path, excel_config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + "*.tmp")
    data.to_parquet(temporary_path, index=False)
    temporary_path.replace(output_path)
    return output_path


def validate_required_columns(df, required_columns, path):
    """Raise an error when a source file is missing configured columns."""
    required = set(required_columns or [])
    actual = {str(column).strip() for column in df.columns}
    missing = sorted(required - actual)

    if missing:
        raise ValueError(
            f"Missing required column(s) in {path.name}: {', '.join(missing)}"
        )


def loaded(con, pipeline, path, digest):
    """Check metadata to see whether this exact file version loaded successfully."""
    return (
        con.execute(
            "SELECT count(*) FROM metadata.file_history WHERE pipeline_name=? AND source_file? AND file_hash=? AND status='SUCCESS",
            [pipeline, str(path.resolve()), digest],
        ).fetchone()[0]
        > 0
    )


def metadata_unchanged(con, pipeline, path):
    """Return whether a successful load has the same size and modified time."""
    stat = path.stat()
    return (
        con.execute(
            "SELECT count(*) FROM metadata.file_history "
            "WHERE pipeline_name=? AND source_file=? AND file_size_bytes=? "
            "AND file_modified_at=? AND status='SUCCESS'",
            [
                pipeline,
                str(path.resolve()),
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime),
            ],
        ).fetchone()[0]
        > 0
    )
