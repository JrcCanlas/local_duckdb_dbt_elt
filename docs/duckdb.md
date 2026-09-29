# DuckDB

The application database is `database\elt.duckdb`. Close the DuckDB prompt before running Python or dbt.

```cmd
duckdb database\elt.duckdb
```

To open the database in DuckDB's browser UI, run this from the repository root:

```cmd
duckdb -ui database\elt.duckdb
```

You can also run `open_duckdb.bat` to open the database in the DuckDB CLI. The DuckDB CLI must be installed and available on `PATH`. Close the DuckDB UI or prompt before running Python or dbt.

Useful queries:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
ORDER BY table_schema, table_name;

SELECT * FROM bronze.customer LIMIT 10;

SELECT pipeline_name, source_file, file_hash, row_count, loaded_at, status
FROM metadata.file_history
ORDER BY loaded_at DESC;
```

The metadata schema contains `elt_run_log`, `file_history`, `audit_log`, and `watermark`. Bronze rows retain `_source_file`, `_loaded_at`, and `_run_id` lineage columns.
