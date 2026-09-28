"""Ingestion helpers for files, validation, metadata checks, and Bronze loading."""

from pathlib import Path
from datetime import datetime
import hashlib, re
import pandas as pd

SAFE_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def file_hash(path: Path):
    """Compute the SHA-256 digest of a file.

    Args:
        path: Filesystem path to the source file that will be hashed.

    Returns:
        str: Hex-encoded SHA-256 digest of the file contents.
    """

    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_file(path: Path, excel_config=None):
    """Load a CSV or Excel file into a pandas DataFrame.

    Args:
        path: Source file path. Supported suffixes are ``.csv``, ``.xlsx``, and
            ``.xlsm``.
        excel_config: Optional dictionary that may include Excel-specific options
            such as ``sheet_name`` and ``header``.

    Returns:
        pandas.DataFrame: File contents loaded as string columns to preserve raw
        values before downstream business typing in dbt.

    Raises:
        ValueError: If the file extension is not a supported data source.
    """

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        excel_config = excel_config or {}
        return pd.read_excel(
            path,
            sheet_name=excel_config.get("sheet_name", 0),
            header=excel_config.get("header", 0),
            dtype=str,
            engine="openpyxl",
        ).fillna("")
    raise ValueError(f"Unsupported file: {path}")


def convert_excel_to_parquet(path, output_path, excel_config=None, data=None):
    """Convert an Excel file into a Parquet file using a temporary atomic replace.

    Args:
        path: Original Excel file that will be read if ``data`` is not provided.
        output_path: Destination path for the generated Parquet file.
        excel_config: Optional configuration used when reading the Excel source.
        data: Existing pandas DataFrame to write instead of re-reading the source.

    Returns:
        Path: The final output path of the generated Parquet file.
    """
    data = data if data is not None else read_file(path, excel_config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    data.to_parquet(temporary_path, index=False)
    temporary_path.replace(output_path)
    return output_path


def validate_required_columns(df, required_columns, path):
    """Ensure a source dataset contains the configured required columns.

    Args:
        df: pandas DataFrame being validated.
        required_columns: Iterable of column names required by the pipeline.
        path: Source file path used in error reporting.

    Raises:
        ValueError: If any required columns are absent from the loaded DataFrame.
    """
    required = set(required_columns or [])
    actual = {str(column).strip() for column in df.columns}
    missing = sorted(required - actual)

    if missing:
        raise ValueError(
            f"Missing required column(s) in {path.name}: {', '.join(missing)}"
        )


def loaded(con, pipeline, path, digest):
    """Check whether a file has already been loaded successfully in this pipeline.

    Args:
        con: Active DuckDB connection used to query metadata.file_history.
        pipeline: Pipeline name identifying the source of the file.
        path: Source file path to match against the stored file history.
        digest: SHA-256 hash of the file contents.

    Returns:
        bool: True when the same pipeline, source path, and file hash have a
        successful entry in the metadata log.
    """
    return (
        con.execute(
            "SELECT count(*) FROM metadata.file_history WHERE pipeline_name=? AND source_file=? AND file_hash=? AND status='SUCCESS'",
            [pipeline, str(path.resolve()), digest],
        ).fetchone()[0]
        > 0
    )


def metadata_unchanged(con, pipeline, path):
    """Determine whether the file metadata still matches the last successful load.

    This check prevents duplicate ingestion when a file has already been loaded
    successfully and its size and modification timestamp have not changed.

    Args:
        con: Active DuckDB connection used to query file history.
        pipeline: Pipeline name for the record lookup.
        path: Source file path to compare against previous successful loads.

    Returns:
        bool: True if the same file path, size, and modification timestamp were
        already recorded as successful in metadata.
    """
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
    """Load a CSV or Parquet file directly into a Bronze table with lineage metadata.

    Args:
        con: Active DuckDB connection used for the ingestion query.
        table: Destination table name in the form ``schema.table``.
        path: Source file that should be read into the table.
        run_id: Current pipeline run identifier to store in the lineage columns.
        source_path: Optional original source path when the file being ingested is
            a derived or staged artifact. Defaults to ``path`` when omitted.

    Returns:
        int: Number of rows loaded from the source file.

    Raises:
        ValueError: If the target table name is unsafe or the file is not CSV/Parquet.
    """
    if not SAFE_TABLE.fullmatch(table):
        raise ValueError(f"Unsafe table: {table}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        reader = "read_csv(?, header=true, all_varchar=true)"
    elif suffix == ".parquet":
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
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, name],
    ).fetchone()[0]
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
    """Insert DataFrame rows into a Bronze table while adding lineage columns.

    Args:
        con: Active DuckDB connection used for the insert.
        table: Destination table name in the form ``schema.table``.
        df: pandas DataFrame containing the source rows to load.
        path: File path that produced the data, used for the ``_source_file`` field.
        run_id: Current ETL run identifier written to the ``_run_id`` column.

    Returns:
        int: Number of rows appended.

    Raises:
        ValueError: If the target table name is not a valid ``schema.table`` value.
    """
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
    """Delete all existing rows from a Bronze table to support replacement loads.

    Args:
        con: Active DuckDB connection used to clear the table.
        table: Bronze table name in the form ``schema.table``.

    Raises:
        ValueError: If the table name is not a valid ``schema.table`` reference.
    """
    if not SAFE_TABLE.fullmatch(table):
        raise ValueError(f"Unsafe table: {table}")
    schema, name = table.split(".")
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=? AND table_name=?",
        [schema, name],
    ).fetchone()[0]
    if exists:
        con.execute(f"DELETE FROM {table}")
