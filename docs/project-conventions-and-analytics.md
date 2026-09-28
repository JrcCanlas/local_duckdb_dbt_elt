# Project Conventions and Analytics Guide

## What this project is for

This repository is a local-first data pipeline for turning operational files into
trusted, reporting-ready datasets. It is designed for teams that need a repeatable
way to load ERP, workflow, customer, and future source data without requiring a
cloud data platform or dbt Cloud.

The project separates ingestion, transformation, operational metadata, and
reporting exports:

```text
CSV/Excel -> Python ingestion -> DuckDB Bronze -> dbt Silver/Mart -> Parquet/CSV -> Power BI
```

DuckDB is the local analytical database. dbt Core provides SQL transformation,
model dependency management, documentation, and data tests. Python controls the
pipeline run, file discovery, incremental file history, audit logging, and export.

## How it supports the analytics team

The pipeline gives analysts and reporting developers a consistent reporting
surface instead of requiring each dashboard to interpret raw files independently.
It supports the team by providing:

- Repeatable loads from source folders with source-file and run-level lineage.
- Typed, cleaned Silver models where dates, amounts, identifiers, and business
  rules are applied consistently.
- Reporting marts with stable business grains and dashboard-oriented measures.
- Reusable Parquet and optional CSV exports under `exports/powerbi/`.
- Run, file, and audit metadata for troubleshooting and refresh traceability.
- A local workflow suitable for Windows laptops, AVD, Citrix, and scheduled jobs.

The analytics team can use the exported marts in Power BI while the ETL process
uses the DuckDB file. Power BI should not keep the DuckDB database open during an
ETL run.

## Active data products

The active dbt project is `dbt/`. The `local_etl/` directory is only a separate
dbt starter example and is not used by `main.py`.

The enabled operational pipelines are defined in `config/pipelines.yml`:

- **ERP:** loads invoice and supplier transaction files and builds `mart.erp`.
- **Workflow:** loads invoice workflow events and builds `mart.workflow`.
- **Customer:** a supported example pipeline that is currently disabled by default.
- **Sales:** reserved configuration for a future pipeline and currently disabled.

The ERP mart is one row per supplier and invoice number. It combines invoice
amounts and payment data with reporting calculations such as outstanding amount,
paid percentage, days to pay, overdue days, payment timing, and amount variance.

The workflow mart is one row per invoice with workflow events. It includes the
current workflow state, event and stage counts, workflow duration, average event
gap, exception rate, exception flag, and completion flag.

These grains are important: dashboard relationships and measures should not treat
`mart.erp` or `mart.workflow` as raw event or invoice-line tables.

## Project conventions

### Repository paths

- `main.py` is the command-line entry point and pipeline orchestrator.
- `etl/` contains configuration, ingestion, metadata, and export helpers.
- `config/app.yml` contains database, logging, and export settings.
- `config/pipelines.yml` defines source folders, load modes, selectors, and marts.
- `dbt/` is the active dbt Core project.
- `database/etl.duckdb` is the local application database.
- `source/` contains input CSV and Excel files.
- `exports/powerbi/` contains generated reporting files.
- `tests/` contains Python unit tests.
- `docs/` contains setup, operations, lineage, troubleshooting, and design guidance.

### Layer responsibilities

- **Python ingestion:** discovers files, reads source values as strings, loads
  Bronze tables, records metadata, and exports selected marts.
- **Bronze:** preserves source-oriented values and lineage. Do not apply reporting
  business logic here.
- **Silver:** cleans, casts, deduplicates, and validates source data.
- **Mart:** presents reporting-ready columns and calculations at a documented
  business grain.
- **Exports:** creates files for Power BI and other consumers without requiring
  them to query the operational database directly.

### dbt conventions

- Use `source()` for tables created by Python ingestion.
- Use `ref()` for dependencies between dbt models.
- Add a pipeline tag such as `erp` or `workflow` to selectable models.
- Keep model-specific business logic in the appropriate Silver or Mart layer.
- Add model descriptions and column tests in `dbt/models/schema.yml` as models
  become part of the supported reporting surface.
- Preserve the custom schema behavior in
  `dbt/macros/generate_schema_name.sql` unless schema naming is intentionally
  changed.

### Lineage and metadata

Bronze rows retain `_source_file`, `_loaded_at`, and `_run_id`. Operational
metadata belongs in the `metadata` schema:

- `metadata.file_history` tracks source file hashes, row counts, status, and runs.
- `metadata.etl_run_log` records pipeline-level success or failure.
- `metadata.audit_log` records discovery, Bronze, dbt, and export stages.
- `metadata.watermark` stores incremental processing state where configured.

File SHA-256 hashes prevent a successfully loaded file version from being loaded
twice. Only one process should write to `database/etl.duckdb` at a time.

## Reporting practices

For dashboard development:

1. Start with the mart grain documented above before creating relationships or
   measures.
2. Prefer the curated mart calculations for common KPIs so dashboards use the
   same definitions.
3. Keep source file, load timestamp, and run ID available when investigating a
   number that does not match an operational report.
4. Treat null dates and amounts as meaningful data-quality states; do not silently
   convert them to zero in a dashboard.
5. Validate refresh results against the ETL and dbt logs before publishing a
   changed report.
6. Use exported Parquet or CSV files for Power BI consumption, especially when an
   ETL run may write to DuckDB.

Current date-based calculations, such as overdue days and open payment timing,
are evaluated when the mart is built. A refresh is therefore required for those
values to remain current.

## Common development commands

Run commands from the repository root on Windows:

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\dbt.exe parse --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt --select tag:erp
.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt --select +tag:workflow
.venv\Scripts\python.exe main.py --pipeline erp
.venv\Scripts\python.exe main.py --pipeline workflow
```

Use `.venv\Scripts\dbt.exe` directly for dbt commands. Do not run
`python -m dbt` from the repository root because the active project directory is
also named `dbt` and can shadow the installed Python package.

For scheduled operation and failure investigation, see
[operations.md](operations.md). For source-to-output lineage, see
[lineage.md](lineage.md).
