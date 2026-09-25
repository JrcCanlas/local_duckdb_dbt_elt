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


def run_pipeline(db_path, name, cfg, app):
    """Execute a complete ETL pipeline from discovery through final export.

    The flow is: discover source files, validate required columns or Excel inputs,
    load records into the Bronze table, record file metadata, close the DuckDB
    connection for dbt access, run the dbt selector, export mart tables, and
    update the pipeline watermark and run log.

    Args:
        db_path: Filesystem path to the application DuckDB database.
        name: Pipeline identifier used in metadata tables and logging.
        cfg: Pipeline-specific settings loaded from config/pipelines.yml.
        app: Global application configuration loaded from config/app.yml.

    Raises:
        Exception: Any ingestion, validation, dbt, or export failure is recorded in
            metadata and re-raised to stop the run.
    """
    pipeline_started = time.perf_counter()
    run = str(uuid.uuid4())
    found = done = rows = 0
    files = []
    con = connect(db_path)
    con.execute(
        "INSERT INTO metadata.etl_run_log(run_id,pipeline_name,started_at,status) VALUES (?,?,current_timestamp,'RUNNING')",
        [run, name],
    )
    logging.info("[%s] Pipeline started (run_id=%s)", name, run)
    try:
        # Discover files from the folder and pattern selected in pipelines.yml.
        files = sorted((ROOT / cfg["source_folder"]).glob(cfg["source_pattern"]))
        found = len(files)
        logging.info("[%s] Discovery complete: %d file(s) found", name, found)
        audit(con, run, name, "DISCOVERY", "SUCCESS", found, f"Found {found} file(s)")
        append = cfg.get("append", True)
        if not append:
            logging.info(
                "[%s] Replacement mode: clearing %s", name, cfg["bronze_table"]
            )
            clear_bronze(con, cfg["bronze_table"])
        # Hashing lets repeated runs skip files that were already loaded.
        for path in files:
            if append and metadata_unchanged(con, name, path):
                logging.info("[%s] Skipping loaded file: %s", name, path.name)
                continue
            digest = file_hash(path)
            logging.info("[%s] Loading file: %s", name, path.name)
            try:
                if path.suffix.lower() == ".csv":
                    columns = con.execute(
                        "DESCRIBE SELECT * FROM read_csv(?, header=true, all_varchar=true)",
                        [str(path)],
                    ).fetchall()
                    actual_columns = {column[0].strip() for column in columns}
                    required = set(cfg.get("required_columns") or [])
                    missing = sorted(required - actual_columns)
                    if missing:
                        raise ValueError(
                            f"Missing required column(s) in {path.name}: {', '.join(missing)}"
                        )
                    n = append_source_file(con, cfg["bronze_table"], path, run)
                else:
                    df = read_file(path, cfg.get("excel"))
                    validate_required_columns(df, cfg.get("required_columns"), path)
                    staging_folder = ROOT / cfg.get("staging_folder", f"staging/{name}")
                    parquet_path = staging_folder / f"{path.stem}.parquet"
                    convert_excel_to_parquet(
                        path, parquet_path, cfg.get("excel"), data=df
                    )
                    n = append_source_file(
                        con,
                        cfg["bronze_table"],
                        parquet_path,
                        run,
                        source_path=path,
                    )
            except Exception as exc:
                logging.error("[%s] Failed file %s: %s", name, path.name, exc)
                raise
            stat = path.stat()
            done += 1
            rows += n
            con.execute(
                "INSERT INTO metadata.file_history VALUES (?,?,?,?,?,current_timestamp,?,?,'SUCCESS',NULL) "
                "ON CONFLICT (pipeline_name, source_file, file_hash) DO UPDATE SET "
                "file_size_bytes=excluded.file_size_bytes, "
                "file_modified_at=excluded.file_modified_at, "
                "loaded_at=excluded.loaded_at, run_id=excluded.run_id, "
                "row_count=excluded.row_count, status=excluded.status, "
                "error_message=excluded.error_message",
                [
                    name,
                    str(path.resolve()),
                    digest,
                    stat.st_size,
                    datetime.fromtimestamp(stat.st_mtime),
                    run,
                    n,
                ],
            )
            logging.info("[%s] Loaded %d row(s) from %s", name, n, path.name)
        audit(con, run, name, "BRONZE", "SUCCESS", rows)
        # dbt needs exclusive access to the DuckDB file while it builds models.
        logging.info(
            "[%s] Bronze load complete: %d file(s), %d row(s)", name, done, rows
        )
        con.close()  # release DuckDB before dbt opens the same file
        logging.info("[%s] Starting dbt build: %s", name, cfg["dbt_selector"])
        dbt_build(cfg["dbt_selector"], db_path)
        con = connect(db_path)
        audit(con, run, name, "DBT_BUILD", "SUCCESS")
        logging.info("[%s] dbt build complete", name)
        outputs = export_tables(con, cfg["mart_tables"], ROOT, app)
        audit(con, run, name, "EXPORT", "SUCCESS", 0, ",".join(map(str, outputs)))
        logging.info("[%s] Export complete: %s", name, ", ".join(map(str, outputs)))
        wm = max(
            (datetime.fromtimestamp(f.stat().st_mtime) for f in files),
            default=datetime.now(),
        )
        con.execute(
            "INSERT INTO metadata.watermark VALUES (?, ?, current_timestamp, ?) ON CONFLICT(pipeline_name) DO UPDATE SET watermark_value=excluded.watermark_value,updated_at=excluded.updated_at,run_id=excluded.run_id",
            [name, wm, run],
        )
        con.execute(
            "UPDATE metadata.etl_run_log SET ended_at=current_timestamp,status='SUCCESS',files_found=?,files_loaded=?,rows_loaded=? WHERE run_id=?",
            [found, done, rows, run],
        )
        con.close()
        pipeline_runtime = time.perf_counter() - pipeline_started
        logging.info(
            "[%s] Pipeline completed successfully in %s",
            name,
            format_runtime(pipeline_runtime),
        )
    except Exception as exc:
        pipeline_runtime = time.perf_counter() - pipeline_started
        try:
            con.close()
        except Exception:
            pass
        con = connect(db_path)
        con.execute(
            "UPDATE metadata.etl_run_log SET ended_at=current_timestamp,status='FAILED',files_found=?,files_loaded=?,rows_loaded=?,error_message=? WHERE run_id=?",
            [found, done, rows, str(exc), run],
        )
        audit(con, run, name, "PIPELINE", "FAILED", rows, str(exc))
        con.close()
        logging.error(
            "[%s] Pipeline failed after %s", name, format_runtime(pipeline_runtime)
        )
        raise


def main():
    """Run the ETL application for the selected pipeline or every enabled pipeline.

    Command-line usage:
        python main.py --pipeline customer

    The function reads the application and pipeline configuration, ensures the
    runtime folders exist, configures logging, then iterates through every enabled
    pipeline. Each pipeline executes the ETL lifecycle and records the final exit
    status for the process.

    Returns:
        None: The function exits the process with a shell status code rather than
        returning a value.
    """
    p = argparse.ArgumentParser()
    p.add_argument("--pipeline")
    a = p.parse_args()
    app = read_yaml(ROOT / "config/app.yml")
    pipes = read_yaml(ROOT / "config/pipelines.yml")["pipelines"]
    ensure_runtime_folders(pipes, app)
    log = ROOT / app["logging"]["file"]
    log_format = "%(asctime)s | %(levelname)s | %(message)s"
    file_handler = logging.FileHandler(log)
    file_handler.setFormatter(logging.Formatter(log_format))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ConsoleFormatter(log_format))
    logging.basicConfig(
        level=app["logging"]["level"],
        handlers=[file_handler, console_handler],
    )
    overall_started = time.perf_counter()
    chosen = {a.pipeline: pipes[a.pipeline]} if a.pipeline else pipes
    db_path = ROOT / app["database"]
    failed = []
    for name, cfg in chosen.items():
        if cfg.get("enabled", True):
            try:
                run_pipeline(db_path, name, cfg, app)
            except Exception as exc:
                logging.exception("[%s] Pipeline failed: %s", name, exc)
                failed.append(name)
    overall_runtime = time.perf_counter() - overall_started
    logging.info("Overall ETL runtime: %s", format_runtime(overall_runtime))
    if failed:
        print("Failed: " + ", ".join(failed))
        exit_code = 1
    else:
        print("ETL completed successfully.")
        exit_code = 0
    if os.environ.get("ETL_NON_INTERACTIVE") != "1":
        input("Press Enter to close...")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    print("Test run")
