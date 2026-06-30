"""WRDS connection utilities for Compustat, CRSP, and licensed extracts."""

from __future__ import annotations

from typing import Any

from oaa_observatory.config.settings import Settings, get_settings
from oaa_observatory.utils.logging import logger


class WRDSClient:
    """Thin wrapper around the WRDS Python API.

    Requires optional ``wrds`` package and valid credentials in ``.env``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize WRDS client.

        Args:
            settings: Application settings with WRDS credentials.
        """
        self.settings = settings or get_settings()
        self._connection: Any = None

    def connect(self) -> Any:
        """Establish WRDS connection.

        Returns:
            WRDS connection object.

        Raises:
            ImportError: If wrds package is not installed.
            ValueError: If credentials are not configured.
        """
        try:
            import wrds
        except ImportError as exc:
            msg = "wrds package required. Install with: uv sync --extra wrds"
            raise ImportError(msg) from exc

        if not self.settings.wrds_username:
            msg = "WRDS_USERNAME not set in environment"
            raise ValueError(msg)

        logger.info("Connecting to WRDS as {}", self.settings.wrds_username)
        self._connection = wrds.Connection(
            wrds_username=self.settings.wrds_username,
            wrds_password=self.settings.wrds_password,
        )
        return self._connection

    def query(self, sql: str) -> Any:
        """Execute SQL query against WRDS.

        Args:
            sql: SQL query string.

        Returns:
            Query results (typically a pandas DataFrame).
        """
        if self._connection is None:
            self.connect()
        logger.debug("WRDS query: {}", sql[:200])
        return self._connection.raw_sql(sql)

    def get_compustat_identifiers(self, start_year: int = 2010) -> Any:
        """Fetch Compustat firm identifiers for entity resolution.

        Args:
            start_year: Minimum fiscal year to include.

        Returns:
            DataFrame with gvkey, cik, ticker, conm (company name).
        """
        sql = f"""
            SELECT DISTINCT gvkey, cik, tic AS ticker, conm AS company_name
            FROM comp.funda
            WHERE fyear >= {start_year}
              AND indfmt = 'INDL'
              AND datafmt = 'STD'
              AND popsrc = 'D'
              AND consol = 'C'
        """
        return self.query(sql)

    def close(self) -> None:
        """Close WRDS connection if open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("WRDS connection closed")
