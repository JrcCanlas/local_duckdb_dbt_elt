# Operations and Scheduling

The generated `run_scheduled.bat` runs the customer pipeline non-interactively:

```bat
set "ELT_NON_INTERACTIVE=1"
```

In Windows Task Scheduler configure:

- **Program:** `C:\Windows\System32\cmd.exe`
- **Arguments:** `/d /c ""C:\Company\ELT\run_scheduled.bat""`
- **Start in:** `C:\Company\ELT`
- An account with read/write permission to the package folder
- Run whether the user is logged on or not
- Retry failed runs and prevent overlapping instances

Direct CLI runs wait for `Press Enter to close...`; scheduled runs do not wait for input. Pipeline and overall durations are logged as `HH:MM:SS`.

Check these files after a failure:

- `logs\scheduler.log`
- `logs\elt.log`
- `dbt\logs\`
- `database\elt.duckdb` metadata tables

Only one process should write to the DuckDB file at a time. Power BI should consume exported files rather than hold the database open during ELT.
