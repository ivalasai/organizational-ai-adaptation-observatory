# Organizational AI Adaptation Observatory

**SEC filing attention signals for a fixed S&P 500 pilot universe, 2015–2026.**

This repository is data infrastructure, not a research paper. It produces structured firm-year evidence from public SEC filings. It does not compute adaptation indices, composite scores, or latent constructs.

---

## What exists today

| Component | Status |
|-----------|--------|
| Fixed firm universe (100 S&P 500 firms, static CSV) | Real, committed |
| Entity resolution (ticker → CIK via SEC `company_tickers.json`) | Real |
| SEC 10-K / 10-Q ingestion (2015–2026) | Real |
| Firm-year attention features (`ai_mention_count`, `ai_mention_share`, `document_count`) | Real |
| Firm-year panel builder | Real |
| Classifier validation workflow (labeling CSV + metrics script) | Real — **metrics pending your labels** |
| Financial controls (`load_compustat_export`) | Scaffold only — manual CSV import, not in default panel |

## What is explicitly out of scope

- Patents, job postings, earnings calls, product/deployment signals
- WRDS API integration or stored WRDS credentials (permanently — licensed data enters only via files you place on disk)
- Composite indices, adaptation scores, governance signals
- Econometric analysis or regression code

**Financial controls:** not yet merged, pending manual Compustat export — see `load_compustat_export()` in `src/oaa_observatory/financial_controls/compustat_import.py`. The default panel ships with attention signals only.

**Classifier validation:** not complete until you fill `human_ai_mention` (0 or 1) in `data/validation/attention_labeling.csv` — a **blind** file with only `sample_id` and `excerpt` (no keyword counts). Write your labeling rule in `docs/validation/attention_classifier_validation.md` first, then run `oaa validation run`. Do not open `attention_scores.csv` while labeling. Patents/jobs/deployment wait until validation metrics exist and the placebo check looks clean on the labeled subsample.

---

## Quick Start

No credentials required. Optional `.env` only overrides the SEC User-Agent string.

```bash
uv sync --all-extras

# 1. Ingest SEC filings, parse text, extract features
oaa pipeline run sec

# 2. Generate labeling sample + validation template
oaa validation sample
oaa validation run

# 3. Build firm-year panel
oaa panel build
```

After a full run you should see approximately:

- **4,500+** raw filing files under `data/raw/sec/`
- **~1,200** firm-year rows in `data/panel/firm_year_panel.parquet`
- Non-zero `ai_mention_count`, `ai_mention_share`, and `document_count` values

**Why ~1,204 rows, not exactly 1,200?** The panel includes one row per firm-year that has at least one filing in 2015–2026, not a fixed 100×12 grid. The number of firms per year rises from ~94 (2015) to ~106 (2024+) as EDGAR history fills in; there are no duplicate firm-year keys.

**Sanity checks (run these yourself):**

```bash
# Placebo: mentions by year should be near-zero pre-2018, ramping 2022+
uv run python -c "
import pandas as pd
p = pd.read_parquet('data/panel/firm_year_panel.parquet')
print(p.groupby('year')['ai_mention_count'].agg(['sum','mean', lambda s: (s>0).mean()]))
"
```

Observed pattern on the pilot ingest: 2015 mean ≈ 0.01 mentions/firm-year; 2024–2025 mean ≈ 9–12. Early years are essentially flat; the ramp is concentrated in 2023–2025.

Re-running `oaa pipeline run sec` is idempotent: existing raw files and manifest entries are skipped.

The first full download for 100 firms (2015–2026) may take 30–60 minutes due to SEC rate limits.

---

## Firm universe

Static list: `data/universe/firm_universe.csv`

- First 100 S&P 500 constituents by ticker (alphabetical)
- Sourced from [Wikipedia List of S&P 500 companies](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies), snapshot Jan 2026
- GVKEY and PERMNO are intentionally absent; CIK is populated by the SEC bootstrap step

Regenerate the universe CSV (optional):

```bash
uv run python scripts/build_firm_universe.py
```

---

## Manual Compustat import (when you have WRDS access)

Export a CSV from WRDS yourself with columns: `gvkey, cik, fyear, at, roa, sic, emp`.

```python
from oaa_observatory.financial_controls import load_compustat_export, merge_compustat_into_panel

comp = load_compustat_export("path/to/your_compustat_export.csv")
# merge_compustat_into_panel(panel, comp, mapping)  — call manually when ready
```

This function never contacts WRDS.

---

## Design philosophy

1. **Infrastructure, not theory** — structured evidence only; researchers define constructs downstream.
2. **Evidence, not indices** — counts and shares, not composite scores.
3. **Reproducibility** — config-driven pipelines, immutable raw data, staged outputs.
4. **Manual licensed data** — WRDS/Compustat data enters only via files you export and place on disk.

---

## Repository layout

```
data/universe/firm_universe.csv     # static firm list
data/raw/sec/                       # immutable downloaded filings
data/intermediate/sec/              # parsed document text
data/features/attention/sec/        # firm-year attention features
data/panel/                         # assembled panel
data/validation/                    # classifier labeling CSV
configs/datasources/sec.toml
src/oaa_observatory/
  sec/                              # EDGAR client + pipeline
  entity_resolution/
  panel_builder/
  financial_controls/               # manual Compustat import only
  validation/
docs/validation/
tests/
```

---

## Development

```bash
make test       # unit tests (EDGAR API mocked in CI)
make lint
make typecheck
```

---

## License

MIT — see [LICENSE](LICENSE).
