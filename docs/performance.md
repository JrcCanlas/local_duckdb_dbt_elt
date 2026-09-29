# Performance

The ingestion flow is mode-aware:

- CSV files load directly through DuckDB.
- Incremental files are checked by size and modified time before SHA-256 hashing.
- Excel files are parsed once, converted atomically to Parquet, and loaded from Parquet.
- Full-load pipelines still rebuild Bronze and parse their Excel sources on each run by design.

For large files, prefer:

```text
CSV/Excel -> Parquet -> DuckDB -> dbt -> Parquet export
```

A 50-70 MB Excel workbook with about 500,000 rows can use substantially more memory while `openpyxl` and Pandas parse it. On a 16 GB laptop, process one file at a time, keep 20-30 GB of free disk space, and avoid running Power BI against DuckDB during the ELT.

Use `append: true` only when files contain new batches. Keep `append: false` for complete snapshots. If corrected records can arrive in incremental files, deduplicate them in the Silver model using a stable business key.

Keep CSV export disabled unless required:

```yaml
exports:
  parquet: true
  csv: false
```

Measure hashing, reading, Bronze insertion, dbt, and export separately before optimizing the next stage.
