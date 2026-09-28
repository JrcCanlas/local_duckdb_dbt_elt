# Testing the ETL Project

This guide covers running and understanding the unit tests in `tests/test_etl.py`.

## Overview

The test suite validates the Python ETL helpers and core utilities. All tests use **temporary files and an in-memory DuckDB database**, so they do not modify the production database (`database/etl.duckdb`) or exported files.

## Running Tests

Run all tests from the repository root:

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run tests with higher verbosity:

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v --verbosity=2
```

Run a specific test class:

```cmd
.venv\Scripts\python.exe -m unittest tests.test_etl.EtlHelperTests -v
```

Run a specific test method:

```cmd
.venv\Scripts\python.exe -m unittest tests.test_etl.EtlHelperTests.test_file_hash_matches_sha256 -v
```

## Test Coverage

### Configuration Tests

**`test_read_yaml_returns_configuration`**

- Validates that YAML files are correctly parsed into Python dictionaries.
- Ensures settings from `config/app.yml` and `config/pipelines.yml` load properly.

### File Hashing and Deduplication

**`test_file_hash_matches_sha256`**

- Confirms file fingerprints use standard SHA-256 digest.
- Validates that the same file always produces the same hash.
- Used to prevent duplicate ingestion of unchanged source files.

### Data Reading

**`test_read_file_loads_csv_as_strings`**

- Verifies CSV values are loaded as strings (not auto-converted to numbers).
- Ensures data types are preserved from source files.
- Validates that column names are correctly extracted.

**`test_read_file_rejects_unsupported_extensions`**

- Confirms that unsupported file formats (e.g., `.txt`, `.json`) are rejected with clear error messages.
- Currently supports: `.csv`, `.xlsx`, `.xlsm` files.

### Bronze Layer Ingestion

**`test_append_bronze_adds_lineage_and_duplicate_check_works`**

- Validates that lineage columns are added during ingestion:
  - `_source_file`: Full path to the source file
  - `_loaded_at`: Timestamp of the load
  - `_run_id`: Unique identifier for the ETL run
- Tests duplicate detection by checking the `metadata.file_history` table.
- Confirms that a file loaded once cannot be loaded twice using `loaded()` function.

**`test_clear_bronze_removes_existing_rows`**

- Validates the "replace" load mode by confirming old rows are removed before new ones are inserted.
- Used for full-load pipelines where snapshots replace previous data.

### Metadata Tracking

**`test_metadata_unchanged_detects_successful_file_version`**

- Confirms the "incremental" load mode optimization.
- Files with unchanged size and modification time can skip re-hashing.
- Validates that previous successful loads are recognized.

### Direct File Ingestion

**`test_append_source_file_loads_csv_without_pandas`**

- Tests DuckDB-native CSV loading (using `read_csv()`).
- Bypasses pandas for improved performance with large files.
- Confirms lineage columns are preserved during native ingestion.

### Excel to Parquet Conversion

**`test_convert_excel_to_parquet`**

- Validates Excel file conversion to Parquet format.
- Uses atomic file replacement (temporary file + rename) for safety.
- Parquet format improves DuckDB loading performance for repeated ingestions.
- Confirms data integrity through round-trip verification.

### Export Functionality

**`test_export_tables_writes_parquet_and_csv`**

- Validates that Mart tables are exported in configured formats.
- Tests both Parquet (efficient for BI tools) and CSV (universal compatibility).
- Confirms exports are written to `exports/powerbi/` with correct naming.

**`test_table_names_are_validated_before_export`**

- Security validation: ensures table names are schema-qualified identifiers.
- Prevents SQL injection by rejecting dangerous identifiers.
- Example: `mart.customer; DROP TABLE metadata.audit_log` is rejected.

## Test Environment

Each test runs in isolation:

- **Setup**: A fresh in-memory DuckDB connection is created with metadata schema initialized.
- **Test execution**: The test runs against temporary files and the in-memory database.
- **Teardown**: The connection is closed, and all temporary files are cleaned up.

This isolation ensures:

- Tests don't interfere with each other.
- No side effects on production data.
- Tests run quickly without disk I/O to the actual database.

## Integration with CI/CD

To run tests as part of automated validation:

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v && echo Tests passed!
```

Or with error codes:

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 (
  echo Tests failed with error code %errorlevel%
  exit /b %errorlevel%
)
```

## Validation Checklist

After modifying Python ETL code (`etl/*.py`):

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All tests should pass. If tests fail:

1. Review the test output for the specific assertion that failed.
2. Check the error message for clues about what changed.
3. Verify that the change is intentional.
4. Update the test if the new behavior is correct.

After changing dbt code or configuration:

```cmd
.venv\Scripts\dbt.exe parse --project-dir dbt --profiles-dir dbt
.venv\Scripts\dbt.exe build --project-dir dbt --profiles-dir dbt
```

These dbt commands have their own test suite defined in `dbt/models/schema.yml`.

## Extending Tests

To add a new test:

1. Add a method to `EtlHelperTests` class in `tests/test_etl.py`.
2. Start the method name with `test_`.
3. Use `tempfile.TemporaryDirectory()` for file I/O.
4. Use `self.connection` (in-memory database) for data operations.
5. Use `self.assert*` methods for validation.

Example:

```python
def test_my_new_feature(self):
    """Describe what is being tested."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "test_file.csv"
        path.write_text("col1,col2\nval1,val2\n", encoding="utf-8")

        # Call the function being tested
        result = my_function(path)

        # Assert the expected outcome
        self.assertEqual(expected_value, result)
```

## See Also

- [Developer setup](setup.md)
- [Troubleshooting](troubleshooting.md)
- [dbt development](dbt.md)
