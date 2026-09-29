# Developer Setup

This project runs locally on Windows with Python, DuckDB, and dbt Core. The active dbt project is `dbt/`; `local_elt/` is a separate starter example and is not used by `main.py`.

## Using uv

Install `uv` with WinGet:

```cmd
winget install --id=astral-sh.uv -e
```

Or install it from PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

From the repository root:

```cmd
uv python install 3.12
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

The `.venv` layout is compatible with the batch launchers, scheduler, and packager. Install build dependencies when packaging:

```cmd
uv pip install --python .venv\Scripts\python.exe -r requirements-build.txt
```

## Using Python and pip

```cmd
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Validate and run

```cmd
.venv\Scripts\dbt.exe debug --project-dir dbt --profiles-dir dbt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe main.py --pipeline customer
```

Run every enabled pipeline with:

```cmd
.venv\Scripts\python.exe main.py
```

Logs are written to `logs\elt.log`. The first run creates configured source, staging, database, export, and log folders automatically.
