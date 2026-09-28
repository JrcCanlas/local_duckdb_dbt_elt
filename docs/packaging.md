# Client Packaging

PyInstaller creates a client package that runs without a Python installation. Build it from the repository root:

```cmd
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe build_package.py
```

The output is `dist\etl_client\`:

```text
dist\etl_client\
├── etl_runner.exe
├── dbt.exe
├── run_scheduled.bat
├── config\
├── dbt\
├── source\
├── staging\
├── database\
├── exports\
└── logs\
```

Copy the complete folder to a writable client location. Do not copy `.venv`, `build`, or the development database unless existing data is intentionally being deployed. Place client files in the appropriate `source\` folder.

Test the package:

```cmd
cd /d C:\Company\ETL
etl_runner.exe --help
etl_runner.exe --pipeline customer
```

The output is written to `exports\powerbi\`; logs are written to `logs\etl.log`. Excel files are cached as Parquet under `staging\<pipeline>` before being loaded.

PyInstaller reduces casual source visibility but is not a security boundary. dbt models and runtime configuration remain external and can be inspected by a user with access to the laptop.
