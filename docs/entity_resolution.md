# Entity Resolution

## Canonical Firm Identifier

Every firm in the observatory receives a stable `firm_id`:

```
OAA-{12-char-hash}
```

The hash is derived deterministically from the highest-priority available identifier.

## Supported Identifiers

| Type | Source | Example |
|------|--------|---------|
| `gvkey` | Compustat | `001690` |
| `cik` | SEC EDGAR | `0000320193` |
| `cusip` | CRSP / Compustat | `037833100` |
| `permno` | CRSP | `14593` |
| `ticker` | Exchange | `AAPL` |
| `company_name` | Various | `Apple Inc.` |

## Priority Order

When generating a new `firm_id`, identifiers are used in this order:

1. GVKEY
2. CIK
3. CUSIP
4. PERMNO
5. Ticker
6. Company name

## Usage

### Python API

```python
from oaa_observatory.entity_resolution import EntityResolver, IdentifierType
from oaa_observatory.schemas.records import FirmIdentifier

resolver = EntityResolver()

# Register a firm
record = FirmIdentifier(
    firm_id="",
    gvkey="001690",
    cik="0000320193",
    ticker="AAPL",
    source="compustat",
)
firm_id = resolver.register(record)

# Resolve by any identifier
firm_id = resolver.resolve(IdentifierType.TICKER, "AAPL")

# Bulk resolve in a DataFrame
df = resolver.resolve_dataframe(df, "gvkey", IdentifierType.GVKEY)
```

### CLI

```bash
# Register
oaa entity register --gvkey 001690 --cik 0000320193 --ticker AAPL

# Resolve
oaa entity resolve ticker AAPL
```

## Mapping Table

Persisted at `data/intermediate/entity_resolution/mappings.parquet`.

Can be bootstrapped from WRDS Compustat:

```python
from oaa_observatory.wrds import WRDSClient

client = WRDSClient()
identifiers = client.get_compustat_identifiers(start_year=2010)
```

## Design Notes

- Mappings are append-only (upsert by firm_id)
- CIK values are zero-padded to 10 digits
- Tickers are uppercased
- Unresolved identifiers return `None` (not guessed)
