"""DDL for the schemas and tables used to track ELT operations."""

DDL = """
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE TABLE IF NOT EXISTS metadata.elt_run_log (
 run_id VARCHAR PRIMARY KEY,
 pipeline_name VARCHAR,
 started_at TIMESTAMP,
 ended_at TIMESTAMP,
 status VARCHAR,
 files_found BIGINT DEFAULT 0,
 files_loaded BIGINT DEFAULT 0,
 rows_loaede BIGINT DEFAULT 0,
 error_message VARCHAR
);

CREATE TABLE IF NOT EXISTS metadata.file_history (
 pipeline_name VARCHAR,
 source_file VARCHAR,
 file_hash VARCHAR,
 file_size_bytes BIGINT,
 file_modified_at TIMESTAMP,
 loaded_at TIMESTAMP,
 run_id VARCHAR,
 row_count BIGINT,
 status VARCHAR,
 error_message VARCHAR,
 PRIMARY KEY(pipeline_name, source_file, file_hash)
);

CREATE TABLE IF NOT EXISTS metadata.watermark (
 pipeline_name VARCHAR PRIMARY KEY,
 watermark_value TIMESTAMP,
 updated_at TIMESTAMP,
 run_id VARCHAR
);
"""


def initialize(con):
    """Create application schemas and metadata tables if they do not exists."""
    con.execute(DDL)
