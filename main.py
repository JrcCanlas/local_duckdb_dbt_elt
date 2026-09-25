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


def dbt_build(selector, db_path):
    """Execute the configured dbt build for a pipeline and log its output.

    The project intentionally calls the dbt executable directly instead of using
    ``python -m dbt`` because the repository contains a local ``dbt`` directory
    that holds the project itself and would otherwise shadow the package import.

    Args:
        selector: dbt selector string used with ``--select`` to build the desired
            models or tags.
        db_path: Filesystem location of the DuckDB database passed through the
            ETL_DATABASE_PATH environment variable to the dbt process.

    Raises:
        RuntimeError: If the dbt command exits with a non-zero status code.
    """
    dbt_executable = ROOT / "dbt.exe"
    if not dbt_executable.exists():
        dbt_executable = Path(sys.executable).with_name("dbt")
    cmd = [
        str(dbt_executable),
        "build",
        "--project-dir",
        str(ROOT / "dbt"),
        "--profiles-dir",
        str(ROOT / "dbt"),
        "--target-path",
        str(ROOT / "dbt" / "target"),
        "--select",
        selector,
    ]
    environment = dict(os.environ)
    environment["ETL_DATABASE_PATH"] = str(db_path)
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    dbt_error_started = False
    for line in result.stdout.splitlines():
        if "[ERROR]: Encountered an error:" in line:
            dbt_error_started = True
        if dbt_error_started:
            logging.error("[dbt] %s", line)
        else:
            logging.info("[dbt] %s", line)

    if result.returncode != 0:
        raise RuntimeError(
            f"dbt build failed with exit code {result.returncode}. "
            "Review the preceding [dbt] messages for the failing model."
        )


if __name__ == "__main__":
    print("Test run")
