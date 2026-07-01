# Architecture (v0.2)

Single working vertical slice:

```
firm_universe.csv
       ↓
SEC company_tickers.json  →  entity resolution (ticker → CIK → firm_id)
       ↓
SEC EDGAR 10-K/10-Q download  →  data/raw/sec/
       ↓
HTML/XBRL parse  →  data/intermediate/sec/documents.parquet
       ↓
Keyword counter  →  data/features/attention/sec/firm_year.parquet
       ↓
Panel builder  →  data/panel/firm_year_panel.parquet
```

Optional (manual, not in default pipeline):

- `load_compustat_export(path)` — merge WRDS CSV you export yourself
- `oaa validation sample` / `oaa validation run` — classifier validation workflow

WRDS is never contacted by this codebase.
