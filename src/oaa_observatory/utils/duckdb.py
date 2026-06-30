"""DuckDB utilities for analytical pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def get_connection(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection.

    Args:
        db_path: Optional path to persistent database file.
            If ``None``, uses an in-memory database.

    Returns:
        DuckDB connection.
    """
    if db_path is None:
        return duckdb.connect()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def register_dataframe(
    conn: duckdb.DuckDBPyConnection,
    df: pd.DataFrame,
    name: str,
) -> None:
    """Register a pandas DataFrame as a DuckDB view.

    Args:
        conn: Active DuckDB connection.
        df: DataFrame to register.
        name: View name for SQL queries.
    """
    conn.register(name, df)


def query_to_dataframe(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[Any] | None = None,
) -> pd.DataFrame:
    """Execute SQL and return results as a DataFrame.

    Args:
        conn: Active DuckDB connection.
        sql: SQL query string.
        params: Optional query parameters.

    Returns:
        Query results as a pandas DataFrame.
    """
    if params:
        return conn.execute(sql, params).fetchdf()
    return conn.execute(sql).fetchdf()


def load_parquet_glob(
    conn: duckdb.DuckDBPyConnection,
    glob_pattern: str,
    view_name: str,
) -> None:
    """Create a DuckDB view from a Parquet file glob pattern.

    Args:
        conn: Active DuckDB connection.
        glob_pattern: Glob pattern for Parquet files.
        view_name: Name for the resulting view.
    """
    conn.execute(
        f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{glob_pattern}')"
    )
