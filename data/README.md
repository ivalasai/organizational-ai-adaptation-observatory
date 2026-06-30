# Data Directory Layout

This directory holds all pipeline data. **Raw data is never committed to git.**

## Stages

```
data/
├── raw/              # Immutable source downloads (never modified)
├── intermediate/     # Standardized tables (document-level, event-level)
├── features/         # Firm-year signal tables by source
├── panel/            # Assembled firm-year panels
└── exports/          # Researcher-facing exports
```

## Principles

1. **Never overwrite raw data.** Re-ingestion creates new snapshots.
2. **Every stage is reproducible** from config + prior stage inputs.
3. **No derived constructs.** Only structured evidence at each stage.

## Getting Started

Place raw data in the appropriate `raw/` subdirectory, then run:

```bash
oaa pipeline run sec
oaa panel build
```

See `configs/datasources/` for per-source configuration.
