"""Export mart tables to Power BI-friendly file formats."""

from pathlib import Path
import re

SAFE_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_]*$")


def export_tables(con, tables, root, config):
    """Export configured mart tables as Parquet and/or CSV files.

    Args:
        con: Active DuckDB connection with the tables to export.
        tables: Iterable of table names in the form ``schema.table``.
        root: Base project path used to resolve the export directory.
        config: Application configuration dictionary containing the export options.

    Returns:
        list[Path]: A list of exported file paths created during the operation.

    Raises:
        ValueError: If a table name is not in the expected ``schema.table`` format.
    """
    out = root / config["exports"].get("folder", "exports/powerbi")
    out.mkdir(parents=True, exist_ok=True)
    outputs = []
    for table in tables:
        if not SAFE_TABLE.fullmatch(table):
            raise ValueError(f"Unsafe table: {table}")
        stem = table.replace(".", "_")
        if config["exports"].get("parquet", True):
            p = out / f"{stem}.parquet"
            con.execute(
                f"COPY {table} TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(p)]
            )
            outputs.append(p)
        if config["exports"].get("csv", False):
            p = out / f"{stem}.csv"
            con.execute(f"COPY {table} TO ? (HEADER, DELIMITER ',')", [str(p)])
            outputs.append(p)

    return outputs
