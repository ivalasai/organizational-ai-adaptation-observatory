# Project Kernel

## What This Project Is

`organizational-ai-adaptation-observatory` is a reproducible research data pipeline for measuring firm-level AI attention from public SEC filings. It is intentionally infrastructure, not theory: the repo builds structured evidence that downstream research can analyze.

## Current Vertical Slice

The live slice is:

- Fixed 100-firm S&P 500 pilot universe
- SEC identifier bootstrap (`ticker -> CIK`)
- Real 10-K / 10-Q ingestion from EDGAR for 2015-2026
- Text parsing and keyword-based AI mention counting
- Firm-year panel assembly
- Blind human-label validation workflow
- Manual-only Compustat import scaffold

## Explicit Non-Goals

- No patents, jobs, earnings calls, or deployment layers yet
- No WRDS API integration or stored WRDS credentials
- No composite adaptation index
- No econometric modeling inside this repo

## What Has Been Completed

1. Replaced the original multi-layer scaffold with a smaller real end-to-end SEC attention pipeline.
2. Added a committed pilot universe in `data/universe/firm_universe.csv`.
3. Built EDGAR ingestion, parsing, and feature extraction under `src/oaa_observatory/sec/`.
4. Generated real local artifacts from a full pilot ingest:
   - ~4,594 filing documents
   - ~1,204 firm-year panel rows
   - ~4,340 total AI mentions
5. Added validation utilities and CLI commands:
   - `oaa validation sample`
   - `oaa validation run`
6. Updated the validation workflow so human labeling is blind to model output:
   - `data/validation/attention_labeling.csv`
   - `data/validation/attention_scores.csv`
7. Added a manual `load_compustat_export()` path for later financial controls without any live WRDS dependency.
8. Added and passed targeted tests around SEC ingestion, validation, and Compustat import scaffolding.

## What We Learned So Far

- Top-line counts look internally consistent rather than obviously broken.
- The placebo pattern looks plausible: near-zero mentions in early years, with a ramp concentrated in 2023-2025.
- Raw filing spot checks looked directionally correct for both high-mention and low-mention firms.

## Current Status

The SEC attention layer is implemented and pushed. The project is now blocked on validation quality, not pipeline construction.

## Immediate Next Step

Before adding any new layer, complete the human labeling pass:

1. Write a one-sentence labeling rule in `docs/validation/attention_classifier_validation.md`.
2. Fill `human_ai_mention` in `data/validation/attention_labeling.csv`.
3. Run `oaa validation run`.
4. Inspect false positives and false negatives separately.

Only after that should the project expand to patents or other signals.
