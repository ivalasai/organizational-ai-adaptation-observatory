# Organizational AI Adaptation Observatory

**Longitudinal firm-level AI adaptation signal infrastructure from public and commercial sources.**

[![CI](https://github.com/organizational-ai-adaptation/organizational-ai-adaptation-observatory/actions/workflows/ci.yml/badge.svg)](https://github.com/organizational-ai-adaptation/organizational-ai-adaptation-observatory/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Motivation

Empirical research on organizational AI adaptation requires clean, reproducible, longitudinal data about what firms **discuss**, **invest in**, and **deploy**. Today, every research team rebuilds these datasets from scratch — downloading SEC filings, parsing earnings calls, counting patents, scraping job postings — with inconsistent methods and non-comparable results.

The Observatory solves this the way **WRDS** solves financial data or **Compustat** solves accounting data: it provides the infrastructure. Researchers bring the theory.

> Compustat doesn't know what ROA means theoretically. It simply provides clean infrastructure. This repository does the same for organizational AI signals.

## What This Repository Is

- A **modular data pipeline** that ingests public and commercial sources
- A **canonical entity resolution** system mapping GVKEY, CIK, ticker, CUSIP, and PERMNO to stable firm identifiers
- A **firm-year panel builder** that joins signal layers into structured evidence tables
- **Reproducible infrastructure** designed for 5–10 empirical papers over many years

## What This Repository Is Not

- Not an AI Adaptation Index, readiness score, or maturity model
- Not a sentiment analyzer or hype detector
- Not tied to any single paper, theory, or construct
- Not a source of governance signals (CAO appointments, board committees, etc.)
- Not a regression toolkit or econometric framework

Researchers operationalize adaptation constructs downstream. The Observatory provides the evidence.

---

## Signal Layers

Three orthogonal layers of organizational AI evidence:

| Layer | Question | Data Sources | Example Outputs |
|-------|----------|--------------|-----------------|
| **Attention** | What does the firm discuss? | SEC filings, earnings calls, annual reports | `ai_mention_count`, `ai_mention_share`, `document_count` |
| **Investment** | What does the firm invest in? | Patents, job postings, hiring data | `ai_patent_count`, `ai_job_posting_count`, `ai_hiring_intensity` |
| **Deployment** | What does the firm ship? | Product launches, API releases, documentation | `product_launch_count`, `api_launch_count`, `total_deployment_events` |

Each layer outputs **firm-year structured evidence** — counts, shares, and event tallies. No composite indices. No latent variables.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         External Data Sources            │
                    │  SEC EDGAR │ Earnings Calls │ USPTO     │
                    │  Job Boards │ Product Pages │ WRDS       │
                    └──────────┬──────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Entity Resolution  │
                    │  GVKEY/CIK/Ticker →  │
                    │     firm_id (OAA-)   │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
   │  Attention   │     │ Investment  │     │ Deployment  │
   │  Pipeline    │     │  Pipeline   │     │  Pipeline   │
   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Panel Builder     │
                    │  firm_id × year join │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Quality Checks     │
                    │   Parquet / CSV /    │
                    │   DuckDB Exports     │
                    └─────────────────────┘
```

### Data Stages

```
raw/  →  intermediate/  →  features/  →  panel/  →  exports/
```

Raw data is **never overwritten**. Every stage is reproducible from configuration files.

See [docs/architecture.md](docs/architecture.md) for detailed design documentation.

---

## Installation

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/) (recommended) or pip.

```bash
git clone https://github.com/organizational-ai-adaptation/organizational-ai-adaptation-observatory.git
cd organizational-ai-adaptation-observatory

# Install with uv
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"

# Configure credentials
cp .env.example .env
# Edit .env with WRDS credentials, SEC user agent, etc.

# Install pre-commit hooks
uv run pre-commit install
```

---

## Quick Start

```bash
# List available pipelines
oaa pipeline list

# Run a single data source pipeline
oaa pipeline run sec

# Register firm identifiers
oaa entity register --gvkey 001690 --cik 0000320193 --ticker AAPL

# Resolve an identifier
oaa entity resolve ticker AAPL

# Build firm-year panel from feature tables
oaa panel build --config configs/pipeline/panel_builder.toml

# Validate panel quality
oaa panel validate data/panel/firm_year_panel.parquet
```

### Python API

```python
from oaa_observatory.entity_resolution import EntityResolver, IdentifierType
from oaa_observatory.panel_builder import PanelBuilder
from oaa_observatory.sec import SECFilingsPipeline

# Run SEC attention pipeline
pipeline = SECFilingsPipeline()
pipeline.run()

# Build panel
builder = PanelBuilder.from_config_file("configs/pipeline/panel_builder.toml")
panel_path = builder.run()
```

See [examples/](examples/) for complete workflows.

---

## Repository Structure

```
organizational-ai-adaptation-observatory/
├── README.md
├── LICENSE
├── pyproject.toml
├── Makefile
├── configs/                    # TOML configuration files
│   ├── default.toml
│   ├── datasources/            # Per-source configs
│   └── pipeline/               # Panel builder config
├── schemas/                    # JSON schemas for output tables
├── src/oaa_observatory/        # Main package
│   ├── config/                 # Settings and config loading
│   ├── entity_resolution/      # Canonical firm_id mapping
│   ├── ingestion/              # BasePipeline interface
│   ├── sec/                    # Attention: SEC filings
│   ├── earnings_calls/         # Attention: transcripts
│   ├── patents/                # Investment: AI patents
│   ├── jobs/                   # Investment: job postings
│   ├── products/               # Deployment: product evidence
│   ├── nlp/                    # Keyword counting utilities
│   ├── panel_builder/          # Firm-year panel assembly
│   ├── quality_checks/         # Data validation
│   └── wrds/                   # WRDS client wrapper
├── tests/
├── examples/
├── scripts/
├── docs/
└── data/                       # Pipeline data (not committed)
```

---

## Configuration

All data sources are configured via TOML files. No hardcoded paths.

```toml
# configs/datasources/sec.toml
name = "sec_filings"
signal_layer = "attention"
start_year = 2010
ai_keywords = ["machine learning", "artificial intelligence"]
```

Credentials live only in `.env`:

```bash
WRDS_USERNAME=your_username
WRDS_PASSWORD=your_password
SEC_USER_AGENT=YourName your.email@university.edu
```

---

## Data Sources

| Source | Layer | Status | Access |
|--------|-------|--------|--------|
| SEC EDGAR (10-K, 10-Q, 8-K) | Attention | Skeleton | Public |
| Earnings call transcripts | Attention | Skeleton | Licensed (Refinitiv, FactSet) |
| USPTO patents (CPC G06N) | Investment | Skeleton | Public / WRDS |
| AI job postings | Investment | Skeleton | Public / Licensed |
| Product & API launches | Deployment | Skeleton | Public |
| Compustat / CRSP identifiers | Entity resolution | Supported | WRDS |

Full ingestion implementations are added incrementally. The architecture supports plugging in new sources without modifying existing pipelines.

---

## Entity Resolution

All sources map to a canonical `firm_id` (format: `OAA-{hash}`).

Supported identifiers: **GVKEY**, **CIK**, **Ticker**, **CUSIP**, **PERMNO**, **Company name**.

```python
from oaa_observatory.entity_resolution import EntityResolver

resolver = EntityResolver()
firm_id = resolver.resolve("ticker", "AAPL")
```

See [docs/entity_resolution.md](docs/entity_resolution.md).

---

## Design Philosophy

1. **Infrastructure, not theory.** The Observatory collects signals; researchers define constructs.
2. **Evidence, not indices.** Output columns are counts and shares, not composite scores.
3. **Reproducibility by default.** Config-driven pipelines, immutable raw data, staged outputs.
4. **Modularity.** Each data source is an independent pipeline sharing common interfaces.
5. **Extensibility.** New sources, signal layers, and identifier types plug in without refactoring.

---

## Development

```bash
make install-dev   # Install with dev dependencies
make lint          # Ruff linter
make format        # Auto-format
make typecheck     # Mypy strict mode
make test          # Pytest
make test-cov      # With coverage
```

See [docs/contributing.md](docs/contributing.md) for contribution guidelines.

---

## Limitations

- **v0.1 is architecture-first.** Ingestion pipelines are skeletons; researchers provide raw data or connect licensed sources.
- **No sentiment analysis.** Attention signals are mention counts, not tone or hype measures.
- **Public data only.** No internal telemetry, employee monitoring, or proprietary ERP data.
- **US-centric defaults.** Identifier systems and data sources default to US public markets; international extension is planned.
- **No governance layer.** CAO appointments, board AI committees, and similar signals are explicitly excluded.

---

## Roadmap

- [ ] SEC EDGAR bulk download and parsing
- [ ] WRDS Compustat identifier bootstrap script
- [ ] USPTO patent CPC classification pipeline
- [ ] Refinitiv earnings call transcript connector
- [ ] Job posting aggregator (Revelio, LinkUp, or similar)
- [ ] Product launch detection from press releases and changelogs
- [ ] International firm support (ISIN, SEDOL, LEI)
- [ ] Polars-native pipeline option for large-scale processing
- [ ] Databricks / cloud execution templates
- [ ] Versioned dataset releases with DOI

---

## Citation

If you use this infrastructure in your research, please cite the repository:

```bibtex
@software{oaa_observatory,
  title  = {Organizational AI Adaptation Observatory},
  year   = {2026},
  url    = {https://github.com/organizational-ai-adaptation/organizational-ai-adaptation-observatory}
}
```

---

## License

MIT License. See [LICENSE](LICENSE).
