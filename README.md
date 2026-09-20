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

## Project Flow

```text
CSV/Excel Source Files
        |
        v
Python ETL Orchestrator
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
