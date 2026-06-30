"""Reusable entity resolution for mapping firm identifiers to canonical firm_id."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import pandas as pd

from oaa_observatory.schemas.records import FirmIdentifier
from oaa_observatory.utils.io import read_parquet_if_exists, stable_hash, write_parquet_atomic
from oaa_observatory.utils.logging import logger


class IdentifierType(str, Enum):
    """Supported firm identifier types."""

    GVKEY = "gvkey"
    CIK = "cik"
    TICKER = "ticker"
    CUSIP = "cusip"
    PERMNO = "permno"
    COMPANY_NAME = "company_name"


class EntityResolver:
    """Resolve heterogeneous firm identifiers to a canonical ``firm_id``.

    The canonical ``firm_id`` is a stable hash prefix derived from the
    strongest available identifier (GVKEY > CIK > CUSIP > PERMNO > ticker).

    Researchers can join external datasets by any supported identifier type.
    """

    PRIORITY: tuple[IdentifierType, ...] = (
        IdentifierType.GVKEY,
        IdentifierType.CIK,
        IdentifierType.CUSIP,
        IdentifierType.PERMNO,
        IdentifierType.TICKER,
    )

    def __init__(self, mapping_table: pd.DataFrame | None = None) -> None:
        """Initialize resolver with an optional pre-loaded mapping table.

        Args:
            mapping_table: DataFrame with columns matching ``FirmIdentifier``.
        """
        self._mapping = mapping_table if mapping_table is not None else self._empty_mapping()

    @staticmethod
    def _empty_mapping() -> pd.DataFrame:
        columns = [
            "firm_id",
            "gvkey",
            "cik",
            "ticker",
            "cusip",
            "permno",
            "company_name",
            "source",
        ]
        return pd.DataFrame(columns=columns)

    @staticmethod
    def _is_missing(value: object) -> bool:
        if value is None:
            return True
        return isinstance(value, float) and bool(pd.isna(value))

    @staticmethod
    def _normalize_cik(cik: object) -> str | None:
        if EntityResolver._is_missing(cik):
            return None
        return str(int(str(cik).lstrip("0") or "0")).zfill(10)

    @staticmethod
    def _normalize_ticker(ticker: object) -> str | None:
        if EntityResolver._is_missing(ticker):
            return None
        return str(ticker).upper().strip()

    def generate_firm_id(
        self,
        *,
        gvkey: str | None = None,
        cik: str | None = None,
        ticker: str | None = None,
        cusip: str | None = None,
        permno: int | None = None,
        company_name: str | None = None,
    ) -> str:
        """Generate a canonical firm_id from available identifiers.

        Args:
            gvkey: Compustat GVKEY.
            cik: SEC CIK.
            ticker: Exchange ticker symbol.
            cusip: CUSIP identifier.
            permno: CRSP PERMNO.
            company_name: Company name (lowest priority fallback).

        Returns:
            Canonical firm_id string prefixed with ``OAA-``.
        """
        seed: str | None = None
        if gvkey is not None and str(gvkey).strip():
            seed = f"gvkey:{str(gvkey).strip()}"
        elif cik is not None:
            seed = f"cik:{self._normalize_cik(cik)}"
        elif cusip is not None and str(cusip).strip():
            seed = f"cusip:{str(cusip).strip()}"
        elif permno is not None:
            seed = f"permno:{int(permno)}"
        elif ticker is not None:
            seed = f"ticker:{self._normalize_ticker(ticker)}"
        elif company_name is not None and company_name.strip():
            normalized = company_name.strip().upper()
            seed = f"name:{normalized}"

        if seed is None:
            msg = "At least one identifier is required to generate firm_id"
            raise ValueError(msg)

        return f"OAA-{stable_hash(seed, length=12)}"

    def register(self, record: FirmIdentifier) -> str:
        """Register a firm identifier mapping.

        Args:
            record: Firm identifier record.

        Returns:
            Canonical firm_id.
        """
        firm_id = record.firm_id or self.generate_firm_id(
            gvkey=record.gvkey,
            cik=record.cik,
            ticker=record.ticker,
            cusip=record.cusip,
            permno=record.permno,
            company_name=record.company_name,
        )

        row = {
            "firm_id": firm_id,
            "gvkey": record.gvkey,
            "cik": self._normalize_cik(record.cik) if record.cik else None,
            "ticker": self._normalize_ticker(record.ticker),
            "cusip": record.cusip,
            "permno": record.permno,
            "company_name": record.company_name,
            "source": record.source,
        }

        # Upsert: remove existing row with same firm_id, append new
        self._mapping = self._mapping[self._mapping["firm_id"] != firm_id]
        self._mapping = pd.concat([self._mapping, pd.DataFrame([row])], ignore_index=True)
        logger.debug("Registered firm_id={} from source={}", firm_id, record.source)
        return firm_id

    def resolve(
        self,
        identifier_type: IdentifierType | str,
        value: str | int,
    ) -> str | None:
        """Resolve an identifier to a canonical firm_id.

        Args:
            identifier_type: Type of identifier (gvkey, cik, ticker, etc.).
            value: Identifier value.

        Returns:
            Canonical firm_id or ``None`` if not found.
        """
        id_type = IdentifierType(identifier_type)
        column = id_type.value

        if self._mapping.empty:
            return None

        lookup_value: str | int = value
        if id_type == IdentifierType.CIK:
            lookup_value = self._normalize_cik(str(value)) or ""
        elif id_type == IdentifierType.TICKER:
            lookup_value = self._normalize_ticker(str(value)) or ""
        elif id_type == IdentifierType.PERMNO:
            lookup_value = int(value)

        matches = self._mapping[self._mapping[column] == lookup_value]
        if matches.empty:
            return None
        return str(matches.iloc[0]["firm_id"])

    def resolve_dataframe(
        self,
        df: pd.DataFrame,
        identifier_column: str,
        identifier_type: IdentifierType | str,
        output_column: str = "firm_id",
    ) -> pd.DataFrame:
        """Add canonical firm_id column to a DataFrame.

        Unresolved rows receive ``None`` in the output column.

        Args:
            df: Input DataFrame.
            identifier_column: Column containing identifiers to resolve.
            identifier_type: Type of identifier in the column.
            output_column: Name for the resolved firm_id column.

        Returns:
            DataFrame with resolved firm_id column added.
        """
        result = df.copy()

        def _resolve_row(val: object) -> str | None:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            return self.resolve(identifier_type, val)  # type: ignore[arg-type]

        result[output_column] = result[identifier_column].map(_resolve_row)
        resolved = result[output_column].notna().sum()
        logger.info(
            "Resolved {}/{} rows via {} -> firm_id",
            resolved,
            len(result),
            identifier_type,
        )
        return result

    @property
    def mapping_table(self) -> pd.DataFrame:
        """Return the full identifier mapping table."""
        return self._mapping.copy()

    def save(self, path: Path) -> Path:
        """Persist mapping table to Parquet.

        Args:
            path: Output Parquet path.

        Returns:
            Path to written file.
        """
        return write_parquet_atomic(self._mapping, path)

    @classmethod
    def load(cls, path: Path) -> EntityResolver:
        """Load resolver from a persisted mapping table.

        Args:
            path: Parquet file path.

        Returns:
            EntityResolver with loaded mappings.
        """
        df = read_parquet_if_exists(path)
        if df is None:
            return cls()
        return cls(mapping_table=df)
