# Local DuckDB + dbt Core ELT

ELT project for Windows laptops, AVD, and Citrix:

```text
CSV/Excel -> Python ingestion -> DuckDB Bronze -> dbt Silver/Mart -> Parquet/CSV -> Power BI
```

The project supports CSV and Excel ingestion, incremental file-history
tracking, full-load pipelines, dbt transformations and tests, audit metadata,
and Power BI-friendly exports. The enabled ERP and workflow pipelines provide curated invoice and workflow marts for analytical reporting.

## Synthetic data source generated from this project:

- [CSV/Excel ERP/Workflow Invoice Generator](https://github.com/JrcCanlas/raw-csv_excel-invoice-generator)

## High-Level Architecture

![High Level Architecture](images/High%20Level%20Architecture.jpg)

## Low-Level Architecture

![Low Level Architecture](images/Low%20Level%20Architecture.jpg)

## Project Flow

```text
CSV/Excel Source Files
        |
        v
Python ELT Orchestrator
        |
        v
DuckDB Bronze Layer
        |
        v
dbt Silver Transformation Layer
        |
        v
dbt Mart Layer
        |
        v
Parquet/CSV Exports
        |
        v
Power BI
```

## Project Structure

```text
local_duckdb_dbt_elt/
├── config/
│   ├── app.yml
│   └── pipelines.yml
├── database/
│   └── elt.duckdb
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── macros/
│   ├── models/
│   ├── logs/
│   └── target/
├── docs/
│   ├── dbt.md
│   ├── duckdb.md
│   ├── lineage.md
│   ├── operations.md
│   ├── packaging.md
│   ├── performance.md
│   ├── project-conventions-and-analytics.md
│   ├── setup.md
│   ├── testing.md
│   └── troubleshooting.md
├── elt/
│   ├── __init__.py
│   ├── config.py
│   ├── export.py
│   ├── ingest.py
│   └── metadata.py
├── exports/
│   └── powerbi/
├── images/
├── logs/
├── source/
│   ├── customer/
│   ├── erp/
│   └── workflow/
├── staging/
├── tests/
│   └── test_elt.py
├── main.py
├── README.md
├── requirements.txt
├── LICENSE
├── run_customer.bat
├── run_all.bat
└── .gitignore
```

## Documentation

- [Project conventions and analytics guide](docs/project-conventions-and-analytics.md)
- [Developer setup with uv or pip](docs/setup.md)
- [dbt development and commands](docs/dbt.md)
- [DuckDB inspection](docs/duckdb.md)
- [Data lineage](docs/lineage.md)
- [Testing with test_elt.py](docs/testing.md)
- [Performance and load modes](docs/performance.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Client packaging with PyInstaller](docs/packaging.md)
- [Windows Task Scheduler and operations](docs/operations.md)

## Configuration

- `config\app.yml`: database, logging, and CSV/Parquet export settings.
- `config\pipelines.yml`: enabled pipelines, source patterns, load mode,
  Bronze tables, dbt selectors, and mart exports.
- `dbt\profiles.yml`: local DuckDB connection profile.

Set `exports.csv: false` when only Parquet is required. Use `append: true` for
new incremental batches and `append: false` for complete source snapshots.

## Common commands

```cmd
.venv\Scripts\python.exe main.py --pipeline customer
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
```

Logs are written to `logs\elt.log`. Pipeline durations are logged as
`HH:MM:SS`. Configured source, staging, database, export, and log folders are
created automatically when missing.

## Output and metadata

Outputs are written to `exports\powerbi\`. The default customer outputs are:

```text
exports\powerbi\mart_customer.parquet
exports\powerbi\mart_customer.csv
```

Operational metadata is stored in the `metadata` schema:

- `metadata.elt_run_log`
- `metadata.file_history`
- `metadata.audit_log`
- `metadata.watermark`

Only one process should write to `database\elt.duckdb` at a time. Power BI
should consume exported files rather than hold the DuckDB database open during
ELT.
