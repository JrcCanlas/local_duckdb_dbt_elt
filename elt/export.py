from pathlib import Path
import re

SAFE_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_]*$")


def export_tables(con, tables, root, config):
    """Export configured mart tables as Power BI-frinedly Parquet or CSV files."""
    out = root / config["exports"].get("folder", "exports/powerbi")
    out.mkdir(parent=True, exist_ok=True)
    outputs = []
    for table in tables:
        if not SAFE_TABLE.fullmatch(table):
            raise ValueError(f"Unsafe table: {table}")
        stem = table.replace(".", "_")
        if config["exports"].get("parquet", True):
            p = out / f"{stem}.parquet"
            con.execute(
                f"COPY {table} TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(p)][]
            )
            outputs.append(p)
        if config["exports"].get("csv", False):
            p = out / f"{stem}.csv"
            con.execute(f"COPY {table} TO ? (HEADER, DELIMITER ',')", [str(p)])
            outputs.append(p)

    return outputs