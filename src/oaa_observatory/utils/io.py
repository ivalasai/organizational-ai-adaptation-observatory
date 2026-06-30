"""Shared utility functions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.now(tz=UTC).isoformat()


def stable_hash(value: str, length: int = 16) -> str:
    """Generate a stable truncated SHA-256 hash for a string.

    Args:
        value: Input string to hash.
        length: Number of hex characters to return.

    Returns:
        Truncated hexadecimal hash.
    """
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length]


def ensure_parent_dir(path: Path) -> Path:
    """Create parent directories for a file path if needed.

    Args:
        path: Target file path.

    Returns:
        The input path unchanged.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_parquet_atomic(
    df: pd.DataFrame,
    path: Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a DataFrame to Parquet atomically via a temporary file.

    Never overwrites raw data in place; writes to a temp file then renames.

    Args:
        df: DataFrame to persist.
        path: Destination Parquet path.
        metadata: Optional key-value metadata stored in Parquet file metadata.

    Returns:
        Path to the written file.
    """
    ensure_parent_dir(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    table = pa.Table.from_pandas(df, preserve_index=False)
    if metadata:
        existing = table.schema.metadata or {}
        encoded = {k.encode(): str(v).encode() for k, v in metadata.items()}
        table = table.replace_schema_metadata({**existing, **encoded})

    pq.write_table(table, temp_path)  # type: ignore[no-untyped-call]
    temp_path.replace(path)
    return path


def read_parquet_if_exists(path: Path) -> pd.DataFrame | None:
    """Read a Parquet file if it exists.

    Args:
        path: Path to Parquet file.

    Returns:
        DataFrame or ``None`` if the file does not exist.
    """
    if not path.exists():
        return None
    return pd.read_parquet(path)
