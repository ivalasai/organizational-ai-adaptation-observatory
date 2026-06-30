"""Example: entity resolution workflow."""

from oaa_observatory.entity_resolution import EntityResolver
from oaa_observatory.schemas.records import FirmIdentifier


def main() -> None:
    resolver = EntityResolver()

    # Register firms from Compustat/CRSP identifiers
    firms = [
        FirmIdentifier(
            firm_id="",
            gvkey="001690",
            cik="0000320193",
            ticker="AAPL",
            company_name="Apple Inc.",
            source="compustat",
        ),
        FirmIdentifier(
            firm_id="",
            gvkey="012141",
            cik="0000789019",
            ticker="MSFT",
            company_name="Microsoft Corporation",
            source="compustat",
        ),
    ]

    for firm in firms:
        firm_id = resolver.register(firm)
        print(f"{firm.ticker} -> {firm_id}")

    # Save mapping table for pipeline use
    from pathlib import Path

    output = Path("data/intermediate/entity_resolution/mappings.parquet")
    resolver.save(output)
    print(f"\nSaved mappings to {output}")


if __name__ == "__main__":
    main()
