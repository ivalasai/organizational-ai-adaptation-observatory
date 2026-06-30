"""Utility package."""

from oaa_observatory.utils.duckdb import (
    get_connection,
    load_parquet_glob,
    query_to_dataframe,
    register_dataframe,
)
from oaa_observatory.utils.io import (
    ensure_parent_dir,
    read_parquet_if_exists,
    stable_hash,
    utc_now_iso,
    write_parquet_atomic,
)
from oaa_observatory.utils.logging import configure_logging, logger

__all__ = [
    "configure_logging",
    "ensure_parent_dir",
    "get_connection",
    "load_parquet_glob",
    "logger",
    "query_to_dataframe",
    "read_parquet_if_exists",
    "register_dataframe",
    "stable_hash",
    "utc_now_iso",
    "write_parquet_atomic",
]
