# Attention Classifier Validation

Source labels: `data/validation/attention_labeling.csv`

## Labeling rule

_Write your one-sentence rule here before labeling begins, then apply it consistently._

> Example: Count as AI mention (1) only when the excerpt substantively discusses AI/ML
> strategy, products, investment, or operations — not generic risk-factor boilerplate
> that merely names "artificial intelligence" without firm-specific content.

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
