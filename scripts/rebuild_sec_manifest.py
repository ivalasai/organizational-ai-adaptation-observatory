"""Rebuild SEC download manifest from files on disk."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from oaa_observatory.config.settings import get_settings
from oaa_observatory.entity_resolution import EntityResolver
from oaa_observatory.utils.io import write_parquet_atomic


def rebuild_manifest_from_disk(
    mapping_path: Path = Path("data/intermediate/entity_resolution/mappings.parquet"),
    raw_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> Path:
    """Scan ``data/raw/sec/`` and rebuild the download manifest."""
    settings = get_settings()
    raw_root = raw_dir or settings.raw_dir / "sec"
    manifest = manifest_path or raw_root / "download_manifest.parquet"
    resolver = EntityResolver.load(mapping_path)

    rows: list[dict[str, object]] = []
    for cik_dir in raw_root.iterdir():
        if not cik_dir.is_dir():
            continue
        cik_padded = str(int(cik_dir.name)).zfill(10)
        firm_rows = resolver.mapping_table[resolver.mapping_table["cik"] == cik_padded]
        if firm_rows.empty:
            continue
        firm_id = str(firm_rows.iloc[0]["firm_id"])
        ticker = str(firm_rows.iloc[0]["ticker"])
        for accession_dir in cik_dir.iterdir():
            if not accession_dir.is_dir():
                continue
            for filing in accession_dir.iterdir():
                if not filing.is_file() or filing.suffix == ".parquet":
                    continue
                accession = (
                    f"{accession_dir.name[:10]}-{accession_dir.name[10:12]}-{accession_dir.name[12:]}"
                )
                rows.append(
                    {
                        "firm_id": firm_id,
                        "ticker": ticker,
                        "cik": cik_padded,
                        "accession_number": accession,
                        "form_type": "",
                        "filing_date": "",
                        "fiscal_year": 0,
                        "primary_document": filing.name,
                        "raw_path": str(filing.resolve()),
                    }
                )

    df = pd.DataFrame(rows)
    write_parquet_atomic(df, manifest)
    return manifest


if __name__ == "__main__":
    path = rebuild_manifest_from_disk()
    print(f"Rebuilt manifest: {path} ({len(pd.read_parquet(path))} rows)")
