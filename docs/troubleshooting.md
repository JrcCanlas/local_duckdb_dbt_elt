# Troubleshooting

## Scheduled task does not run

Check the Task Scheduler **Program**, **Arguments**, and **Start in** values in [Operations and Scheduling](operations.md). Confirm the task account can write to `database\`, `exports\`, `logs\`, and `staging\`.

## dbt cannot connect

Run:

```cmd
.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
```

Check that `dbt\profiles.yml` uses `ELT_DATABASE_PATH` and that no other process has `database\elt.duckdb` open.

## A file is loaded repeatedly

Check whether its size or modified timestamp changes during copying. For incremental pipelines, wait until the source file is stable before running the ELT.

## Excel processing is slow

This is expected for large `.xlsx` workbooks. Confirm that the Parquet cache under `staging\<pipeline>` is created. Prefer Parquet or CSV from the source system when possible.

## Where to look for errors

- `logs\elt.log`
- `logs\scheduler.log`
- `dbt\logs\`
- `metadata.elt_run_log`
- `metadata.audit_log`

## dbt build errors

The pipeline writes every dbt output line to `logs\elt.log` with a `[dbt]`
prefix. When a dbt build fails, read the `[dbt]` lines immediately before the
pipeline failure message; they contain the model name, file path, and the
underlying dbt error. The final `dbt build failed with exit code ...` message
is only a summary.

For example, this error identifies a model filename that contains a space:

```text
[dbt] Resource names cannot contain spaces:
[dbt] * 'model.local_elt.sample erp' (models\mart\sample erp.sql)
```

Rename the file using an underscore, such as `sample_erp.sql`, then run the
pipeline again. dbt parses the full project before applying a selector, so an
invalid model outside the selected pipeline can still prevent the build.
