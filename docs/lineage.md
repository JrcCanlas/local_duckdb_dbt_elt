# Lineage

The current customer flow is:

```text
source/customer/customer_sample.csv
    |
    v
bronze.customer
    |
    v
silver.customer
    |
    v
mart.customer
    |
    v
exports/powerbi/mart_customer.parquet
```

Python records file-level and run-level lineage in:

- `metadata.file_history`: source path, SHA-256 hash, load time, run ID, row count, and status.
- `metadata.elt_run_log`: pipeline success or failure.
- `metadata.audit_log`: discovery, Bronze, dbt, and export stages.
- Bronze lineage columns: `_source_file`, `_loaded_at`, and `_run_id`.

Generate the dbt lineage documentation with:

```cmd
.venv\Scripts\dbt.exe docs generate --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe docs serve --project-dir dbt --profiles-dir dbt
```
