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


def append_source_file(con, table, path, run_id, source_path=None):
    """Load a CSV or Parquet file directly into Bronze with lineage columns."""
    if not SAFE_TABLE.fullmatch(table):
        raise ValueError(f"Unsafe table: {table}")
    suffix = path.suffix.lower()
    if suffix == "*.csv":
        reader = "read_csv(?, header=true, all_varchar=true)"
    elif suffix == "*.parquet":
        reader = "read_parquet(?)"
    else:
        raise ValueError(f"Direct ingestion does not support: {path}")
    schema, name = table.split(".")
    columns = con.execute(f"DESCRIBE SELECT * FROM {reader}", [str(path)]).fetchall()
    if not columns:
        raise ValueError(f"No columns found in {path.name}")
    source_file = str((source_path or path).resolve())
    loaded_at = datetime.now()
    exists = con.execute(
        "SELECT count(*) FROM information_schema.table WHERE table_schema=? AND table_name=?",
        [schema, name],
    ).fetchon()[0]
    query = (
        f"INSERT INTO {table} BY NAME SELECT *, ? AS _source_file, "
        f"? AS _loaded_at, ? AS _run_id FROM {reader}"
        if exists
        else f"CREATE TABLE {table} AS SELECT *, ? AS _source_file, "
        f"? AS _loaded_at, ? AS _run_id FROM {reader}"
    )
    row_count = con.execute(f"SELECT count(*) FROM {reader}", [str(path)]).fetchone()[0]
    con.execute(
        query,
        [source_file, loaded_at, run_id, str(path)],
    )
    return row_count


def append_bronze(con, table, df, path, run_id):
    """Append source rows to Bronze, adding lineage columns for traceability."""
    if not SAFE_TABLE.fullmatch(table):
        raise ValueError(f"Unsafe table: {table}")
    data = df.copy()
    data["_source_file"] = str(path.resolve())
    data["_loaded_at"] = datetime.now()
    data["_run_id"] = run_id
    con.register("incoming", data)
    schema, name = table.split(".")
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, name],
    ).fetchone()[0]
    con.execute(
        f"INSERT INTO {table} BY NAME SELECT * FROM incoming"
        if exists
        else f"CREATE TABLE {table} AS SELECT * FROM incoming"
    )
    con.unregister("incoming")
    return len(data)


def clear_bronze(con, table):
    """Remove all existing rows from a Bronze table when replacing a load."""
    if not SAFE_TABLE.fullmatch(table):
        raise ValueError(f"Unsafe table: {table}")
    schema, name = table.split(".")
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, name],
    ).fetchone()[0]
    if exists:
        con.execute(f"DELETE FROM {table}")
