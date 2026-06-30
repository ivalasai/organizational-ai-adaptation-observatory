# Data Pipeline

## Staged Data Model

Every data source follows the same four-stage pipeline:

```
raw/ → intermediate/ → features/ → panel/
```

### Stage 1: Raw (`data/raw/`)

- Immutable downloads from external sources
- Never modified after ingestion
- Organized by source subdirectory (e.g., `raw/sec/`)

### Stage 2: Intermediate (`data/intermediate/`)

- Standardized schemas across sources
- Document-level or event-level granularity
- Entity resolution applied (firm_id assigned)

### Stage 3: Features (`data/features/`)

- Firm-year aggregated signals
- Organized by signal layer and source:
  - `features/attention/sec/firm_year.parquet`
  - `features/investment/patents/firm_year.parquet`
  - `features/deployment/products/firm_year.parquet`

### Stage 4: Panel (`data/panel/`)

- Outer-joined firm-year panel across all feature tables
- Column names prefixed by source to avoid collisions
- Quality checks applied before export

## Reproducibility

Each stage output includes Parquet metadata:
- `stage`: pipeline stage name
- `source`: data source identifier
- `signal_layer`: attention | investment | deployment
- `created_at`: ISO timestamp
- `row_count`: number of records

## Configuration

All paths and parameters are configured via TOML files in `configs/`:

```toml
# configs/datasources/sec.toml
name = "sec_filings"
signal_layer = "attention"
start_year = 2010
ai_keywords = ["machine learning", "artificial intelligence"]
```

Credentials belong only in `.env` (never committed).

## Running Pipelines

```bash
# Single source
oaa pipeline run sec

# All sources
python scripts/run_all_pipelines.py

# Build panel
oaa panel build --config configs/pipeline/panel_builder.toml

# Validate panel
oaa panel validate data/panel/firm_year_panel.parquet
```
