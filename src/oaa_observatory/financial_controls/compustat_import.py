"""Manual Compustat CSV import — no live WRDS access."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = frozenset({"gvkey", "cik", "fyear", "at", "roa", "sic", "emp"})
OPTIONAL_COLUMNS = frozenset({"tic", "conm"})


def load_compustat_export(path: Path | str) -> pd.DataFrame:
    """Load a manually exported Compustat annual fundamentals CSV.

    Expected columns (documented layout):
        gvkey, cik, fyear, at, roa, sic, emp
    Optional: tic (ticker), conm (company name)

    The user downloads this file from WRDS themselves and places it on disk.
    This function never contacts WRDS.

    Args:
        path: Path to the CSV export.

    Returns:
        Validated DataFrame with normalized CIK and renamed ``fyear`` → ``year``.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        msg = f"Compustat export not found: {csv_path}"
        raise FileNotFoundError(msg)

    df = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        msg = f"Compustat export missing required columns: {sorted(missing)}"
        raise ValueError(msg)

    result = df.copy()
    result["cik"] = result["cik"].apply(_normalize_cik)
    result = result.rename(columns={"fyear": "year"})
    return result


def merge_compustat_into_panel(
    panel: pd.DataFrame,
    compustat: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    """Join Compustat controls onto a firm-year panel via CIK.

    Args:
        panel: Firm-year panel with ``firm_id`` and ``year``.
        compustat: Output of :func:`load_compustat_export`.
        mapping: Entity resolution table with ``firm_id`` and ``cik``.

    Returns:
        Panel with Compustat columns appended (left join on firm_id + year).
    """
    merged = panel.merge(mapping[["firm_id", "cik"]], on="firm_id", how="left")
    comp = compustat.rename(
        columns={
            "at": "compustat_at",
            "roa": "compustat_roa",
            "sic": "compustat_sic",
            "emp": "compustat_emp",
            "gvkey": "compustat_gvkey",
        }
    )
    return merged.merge(comp, on=["cik", "year"], how="left", suffixes=("", "_dup"))


def _normalize_cik(value: object) -> str:
    if value is None:
        return ""
    text = str(value).split(".")[0]
    if not text or text.lower() == "nan":
        return ""
    return str(int(text)).zfill(10)
