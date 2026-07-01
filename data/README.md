# Data pipeline stages

```
data/universe/firm_universe.csv     # static 100-firm S&P 500 pilot (committed)
data/raw/sec/                       # immutable downloaded filings (not committed)
data/intermediate/sec/              # parsed document text
data/features/attention/sec/        # firm-year attention features
data/panel/                         # assembled panel
data/validation/                    # classifier labeling CSV
```

Run `oaa pipeline run sec` then `oaa panel build`. No credentials required.
