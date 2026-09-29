# dbt

The active dbt Core project is `dbt/`. It uses the local `local_elt` profile and `dbt-duckdb`; dbt Cloud is not required.

```cmd
.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt --select tag:customer
```

`main.py` loads Bronze, closes its DuckDB connection, runs `dbt build`, then exports configured mart tables. Use `source()` for Bronze tables created by Python and `ref()` for dependencies between dbt models.

Other commands:

```cmd
.venv\Scripts\dbt.exe run --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe test --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe docs generate --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe ls --project-dir dbt --profiles-dir dbt --select +mart.customer
```

Generate and open the dbt documentation site from the repository root:

The profile defaults to `database\elt.duckdb` when commands are run from the repository root. Set the database path explicitly only when using a different database. In Command Prompt:

```cmd
set ELT_DATABASE_PATH=database\elt.duckdb
```

In PowerShell:

```powershell
$env:ELT_DATABASE_PATH = "database\elt.duckdb"
```

Then generate and serve the documentation:

```cmd
.venv\Scripts\dbt.exe docs generate --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe docs serve --project-dir dbt --profiles-dir dbt
```

Then open `http://localhost:8080` in a browser. The generated site is built from the project metadata in `dbt\target`; rerun `docs generate` after changing models, sources, or tests. Press `Ctrl+C` in the terminal to stop the local server.

Do not use `python -m dbt` from the repository root because the local `dbt/` project directory can shadow the installed Python package.
