from pathlib import Path
from datetime import datetime
import argparse, logging, os, subprocess, sys, time, uuid
import duckdb
from elt.config import read_yaml
from elt.metadata import initialize
from elt.ingest import (
    file_hash,
    read_file,
    loaded,
    append_bronze,
    append_source_file,
    clear_bronze,
    metadata_unchanged,
    convert_excel_to_parquet,
    validate_required_columns,
)
from elt.export import export_tables

ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)


class ConsoleFormatter(logging.Formatter):
    """Color error message in a interactive console without coloring files."""

    def format(self, record):
        message = super().format(record)
        if record.levelno >= logging.ERROR and sys.stderr.isatty():
            return f"\033[31m{message}\033[0m"
        return message


def connect(db_path):
    """Open DuckDB and make sure the operational metadata tables exists."""
    con = duckdb.connect(str(db_path))
    initialize(con)
    return con


def audit(con, run, pipeline, stage, status, rows=0, msg=None):
    """Record the result of one pipeline stage in the audit log."""
    con.execute(
        "INSERT INTO metadata.audit_log VALUE (?,?,?,?,current_timestamp,?,?,?)",
        [str(uuid.uuid4()), run, pipeline, stage, status, rows, msg],
    )


def format_runtime(seconds):
    """Format elapsed seconds as an easy-to-read hours/minutes/seconds value."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}{minutes:02d}{seconds:02d}"


if __name__ == "__main__":
    print("Test run")
