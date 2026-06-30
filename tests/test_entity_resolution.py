"""Tests for entity resolution."""

from __future__ import annotations

import pandas as pd
import pytest

from oaa_observatory.entity_resolution import EntityResolver, IdentifierType
from oaa_observatory.schemas.records import FirmIdentifier


class TestEntityResolver:
    """Entity resolution test cases."""

    def test_generate_firm_id_from_gvkey(self) -> None:
        resolver = EntityResolver()
        firm_id = resolver.generate_firm_id(gvkey="012345")
        assert firm_id.startswith("OAA-")
        assert len(firm_id) == 16  # OAA- + 12 char hash

    def test_generate_firm_id_deterministic(self) -> None:
        resolver = EntityResolver()
        id1 = resolver.generate_firm_id(gvkey="012345")
        id2 = resolver.generate_firm_id(gvkey="012345")
        assert id1 == id2

    def test_generate_firm_id_priority(self) -> None:
        resolver = EntityResolver()
        from_gvkey = resolver.generate_firm_id(gvkey="001", cik="320193")
        from_cik = resolver.generate_firm_id(cik="320193")
        assert from_gvkey != from_cik

    def test_register_and_resolve(self) -> None:
        resolver = EntityResolver()
        record = FirmIdentifier(
            firm_id="",
            gvkey="012345",
            cik="0000320193",
            ticker="AAPL",
            source="test",
        )
        firm_id = resolver.register(record)
        assert resolver.resolve(IdentifierType.GVKEY, "012345") == firm_id
        assert resolver.resolve(IdentifierType.TICKER, "AAPL") == firm_id

    def test_resolve_dataframe(self) -> None:
        resolver = EntityResolver()
        resolver.register(FirmIdentifier(firm_id="", gvkey="001", ticker="TEST", source="test"))
        df = pd.DataFrame({"gvkey": ["001", "999"], "value": [1, 2]})
        result = resolver.resolve_dataframe(df, "gvkey", IdentifierType.GVKEY)
        assert result.loc[0, "firm_id"] is not None
        assert pd.isna(result.loc[1, "firm_id"])

    def test_requires_identifier(self) -> None:
        resolver = EntityResolver()
        with pytest.raises(ValueError, match="At least one identifier"):
            resolver.generate_firm_id()

    def test_normalize_cik(self) -> None:
        assert EntityResolver._normalize_cik("320193") == "0000320193"
        assert EntityResolver._normalize_cik("0000320193") == "0000320193"
