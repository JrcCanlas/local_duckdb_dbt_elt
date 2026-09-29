"""Unit tests for the local Python ELT helpers.

These tests use temporary files and an in-memory DuckDB database, so they do
not modify database/elt.duckdb or the project's exported files.
"""

import hashlib
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from elt.config import read_yaml
from elt.export import export_tables
from elt.ingest import (
    append_bronze,
    append_source_file,
    clear_bronze,
    convert_excel_to_parquet,
    file_hash,
    loaded,
    metadata_unchanged,
    read_file,
)
from elt.metadata import initialize


class EltHelperTests(unittest.TestCase):
    """Check the small building blocks used by the ETL pipeline."""

    def setUp(self):
        """Create an isolated DuckDB connection for each test."""
        self.connection = duckdb.connect(":memory:")
        initialize(self.connection)

    def tearDown(self):
        """Close the in-memory database after each test."""
        self.connection.close()

    def test_read_yaml_returns_configuration(self):
        """YAML files should be returned as dictionaries."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.yml"
            path.write_text("enabled: true\nitems:\n  - customer\n", encoding="utf-8")

            result = read_yaml(path)

        self.assertEqual({"enabled": True, "items": ["customer"]}, result)

    def test_file_hash_matches_sha256(self):
        """The file fingerprint should be a standard SHA-256 digest."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            contents = b"customer_id,customer_name\n1,Ada\n"
            path.write_bytes(contents)

            result = file_hash(path)

        self.assertEqual(hashlib.sha256(contents).hexdigest(), result)

    def test_read_file_loads_csv_as_strings(self):
        """CSV values remain strings so ingestion does not guess source types."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            path.write_text("customer_id,customer_name\n001,Ada\n", encoding="utf-8")

            result = read_file(path)

        self.assertEqual(["customer_id", "customer_name"], list(result.columns))
        self.assertEqual("001", result.iloc[0]["customer_id"])

    def test_read_file_rejects_unsupported_extensions(self):
        """Unsupported source formats should fail with a useful error."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.txt"
            path.write_text("not a supported table", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported file"):
                read_file(path)

    def test_append_bronze_adds_lineage_and_duplicate_check_works(self):
        """Bronze rows should contain source lineage and load history can skip them."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            path.write_text("customer_id,customer_name\n1,Ada\n", encoding="utf-8")
            digest = file_hash(path)
            data = pd.DataFrame({"customer_id": ["1"], "customer_name": ["Ada"]})

            row_count = append_bronze(
                self.connection, "bronze.customer", data, path, "run-1"
            )
            row = self.connection.execute(
                "SELECT customer_id, customer_name, _source_file, _run_id "
                "FROM bronze.customer"
            ).fetchone()

            self.assertEqual(1, row_count)
            self.assertEqual(("1", "Ada", str(path.resolve()), "run-1"), row)
            self.assertFalse(loaded(self.connection, "customer", path, digest))

            self.connection.execute(
                "INSERT INTO metadata.file_history "
                "(pipeline_name, source_file, file_hash, status) VALUES (?, ?, ?, ?)",
                ["customer", str(path.resolve()), digest, "SUCCESS"],
            )

            self.assertTrue(loaded(self.connection, "customer", path, digest))

    def test_clear_bronze_removes_existing_rows(self):
        """Replacement mode should remove prior Bronze rows before loading."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            data = pd.DataFrame({"customer_id": ["1"], "customer_name": ["Ada"]})
            append_bronze(self.connection, "bronze.customer", data, path, "run-1")

            clear_bronze(self.connection, "bronze.customer")

            count = self.connection.execute(
                "SELECT count(*) FROM bronze.customer"
            ).fetchone()[0]

        self.assertEqual(0, count)

    def test_metadata_unchanged_detects_successful_file_version(self):
        """Incremental loads can skip unchanged files without hashing them."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            path.write_text("customer_id,customer_name\n1,Ada\n", encoding="utf-8")
            stat = path.stat()
            digest = file_hash(path)
            self.connection.execute(
                "INSERT INTO metadata.file_history "
                "(pipeline_name, source_file, file_hash, file_size_bytes, "
                "file_modified_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    "customer",
                    str(path.resolve()),
                    digest,
                    stat.st_size,
                    datetime.fromtimestamp(stat.st_mtime),
                    "SUCCESS",
                ],
            )

            self.assertTrue(metadata_unchanged(self.connection, "customer", path))

    def test_append_source_file_loads_csv_without_pandas(self):
        """DuckDB-native CSV loading should preserve Bronze lineage."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.csv"
            path.write_text("customer_id,customer_name\n1,Ada\n", encoding="utf-8")

            row_count = append_source_file(
                self.connection, "bronze.customer", path, "run-1"
            )
            row = self.connection.execute(
                "SELECT customer_id, customer_name, _source_file, _run_id "
                "FROM bronze.customer"
            ).fetchone()

        self.assertEqual(1, row_count)
        self.assertEqual(("1", "Ada", str(path.resolve()), "run-1"), row)

    def test_convert_excel_to_parquet(self):
        """Excel input can be cached as Parquet for efficient DuckDB loading."""
        with tempfile.TemporaryDirectory() as folder:
            excel_path = Path(folder) / "source.xlsx"
            parquet_path = Path(folder) / "staging" / "source.parquet"
            data = pd.DataFrame({"customer_id": ["1"], "customer_name": ["Ada"]})
            data.to_excel(excel_path, index=False)

            result = convert_excel_to_parquet(excel_path, parquet_path)

            self.assertEqual(parquet_path, result)
            self.assertTrue(parquet_path.exists())
            self.assertEqual(
                [("1", "Ada")],
                self.connection.execute(
                    "SELECT customer_id, customer_name " "FROM read_parquet(?)",
                    [str(parquet_path)],
                ).fetchall(),
            )

    def test_export_tables_writes_parquet_and_csv(self):
        """Configured export formats should be created from a mart table."""
        self.connection.execute(
            "CREATE TABLE mart.customer AS SELECT 1 AS customer_id, 'Ada' AS customer_name"
        )

        with tempfile.TemporaryDirectory() as folder:
            outputs = export_tables(
                self.connection,
                ["mart.customer"],
                Path(folder),
                {"exports": {"folder": "exports", "parquet": True, "csv": True}},
            )

            self.assertEqual(
                {"mart_customer.parquet", "mart_customer.csv"},
                {path.name for path in outputs},
            )
            self.assertTrue(all(path.exists() for path in outputs))

    def test_table_names_are_validated_before_export(self):
        """Only schema-qualified identifier names should reach SQL construction."""
        with self.assertRaisesRegex(ValueError, "Unsafe table"):
            export_tables(
                self.connection,
                ["mart.customer; DROP TABLE metadata.audit_log"],
                Path(tempfile.gettempdir()),
                {"exports": {"parquet": True}},
            )


if __name__ == "__main__":
    unittest.main()
