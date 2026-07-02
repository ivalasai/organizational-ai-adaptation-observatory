# Attention Classifier Validation

Source labels: `data/validation/attention_labeling.csv`

## Labeling rule

Count as AI mention (1) only when the excerpt describes the firm's substantive AI/ML activity or concrete intent (either forward-looking plans/investment/strategy or realized deployment/operations), and label 0 for generic boilerplate/risk-factor language that only mentions AI/ML without firm-specific action, product, or operational context.

## Status

**Pending human labeling.** Fill ``human_ai_mention`` (0 or 1) in the blind labeling CSV
``data/validation/attention_labeling.csv``. That file shows only ``sample_id`` and
``excerpt`` — do not open ``attention_scores.csv`` until labeling is complete.

Then run:

```bash
oaa validation run
```

## Metrics

| Metric | Value |
|--------|------:|
| Precision | _pending_ |
| Recall | _pending_ |
| F1 | _pending_ |

Do not cite this layer as validated until real numbers appear above.
