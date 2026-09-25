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


def ensure_runtime_folders(pipes, app):
    """Create every directory expected by the ETL runtime configuration.

    This establishes the source folders, any staging area required for Excel
    conversions, the export directory for Power BI artifacts, the database file
    parent folder, and the application log directory.

    Args:
        pipes: Mapping of pipeline names to configuration dictionaries from
            config/pipelines.yml.
        app: Application configuration dictionary loaded from config/app.yml.
    """
    source_folders = {
        ROOT / cfg["source_folder"]
        for cfg in pipes.values()
        if cfg.get("source_folder")
    }
    for folder in source_folders:
        folder.mkdir(parents=True, exist_ok=True)
        staging_folders = {
            ROOT / cfg.get("staging_folder", f"staging/{name}")
            for name, cfg in pipes.items()
            if cfg.get("source_pattern", "").lower().endswith((".xlsx", ".xlsm"))
        }
        for folder in staging_folders:
            folder.mkdir(parents=True, exist_ok=True)
    (ROOT / app["exports"].get("folder", "exports/powerbi")).mkdir(
        parents=True, exist_ok=True
    )
    (ROOT / app["database"]).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / app["logging"]["file"]).parent.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print("Test run")
