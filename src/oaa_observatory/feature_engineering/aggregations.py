"""Feature engineering utilities shared across signal layers."""

from __future__ import annotations

import pandas as pd


def to_firm_year(
    df: pd.DataFrame,
    date_column: str,
    firm_id_column: str = "firm_id",  # noqa: ARG001
    year_column: str = "year",
) -> pd.DataFrame:
    """Add firm-year columns from a date column.

    Args:
        df: Input DataFrame with date and firm identifiers.
        date_column: Column containing dates.
        firm_id_column: Column containing firm_id.
        year_column: Name for the derived year column.

    Returns:
        DataFrame with year column added.
    """
    result = df.copy()
    result[year_column] = pd.to_datetime(result[date_column]).dt.year
    return result


def prefix_columns(
    df: pd.DataFrame,
    prefix: str,
    exclude: tuple[str, ...] = ("firm_id", "year"),
) -> pd.DataFrame:
    """Prefix DataFrame columns to avoid name collisions on join.

    Args:
        df: Input DataFrame.
        prefix: Prefix string.
        exclude: Columns to exclude from prefixing.

    Returns:
        DataFrame with prefixed column names.
    """
    rename = {col: f"{prefix}_{col}" for col in df.columns if col not in exclude}
    return df.rename(columns=rename)
