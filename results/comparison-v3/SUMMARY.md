# BIC-Bench V3 Pilot Results

## Model comparison

| Model | Mean | Std. dev. | Parsed-action mean | Pass rate | Blocking matches | Truncated metadata | Verified no-action failures | Wall time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-fable-5-2 | 59.6% | 7.7% | 84.1% | 33.3% | 0 | 0 | 7 | 18.9 min |
| gemini/gemini-4-carbon | 45.0% | 1.8% | 90.0% | 29.2% | 0 | 0 | 12 | 50.1 min |
| openai/gpt-6-astra | 80.0% | 8.0% | 82.6% | 58.3% | 1 | 5 | 0 | 22.3 min |

## Per-task means

| Task | anthropic/claude-fable-5-2 | gemini/gemini-4-carbon | openai/gpt-6-astra |
|---|---:|---:|---:|
| redwood-acme-credit-ledger | 0.0% | 0.0% | 50.0% |
| redwood-audit-export-legal-hold | 90.0% | 0.0% | 93.3% |
| redwood-dedicated-slo-credit | 33.3% | 0.0% | 80.0% |
| redwood-model-catalog-launch | 66.7% | 100.0% | 100.0% |
| redwood-nordbank-residency-commitment | 66.7% | 100.0% | 66.7% |
| redwood-northwind-paid-claim | 70.0% | 80.0% | 100.0% |
| redwood-proxima-exception-renewal | 63.3% | 0.0% | 63.3% |
| redwood-smart-routing-fallback | 86.7% | 80.0% | 86.7% |

## Usage

| Model | API calls | Prompt tokens | Cached tokens | Cache writes | Completion tokens | Reported API cost | Estimated list cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-fable-5-2 | 381 | 14,568,320 | 13,024,202 | 1,543,250 | 357,736 | $0.0000 | $32.35 |
| gemini/gemini-4-carbon | 593 | 19,594,106 | 17,561,570 | 0 | 436,577 | $0.0000 | — |
| openai/gpt-6-astra | 305 | 4,781,893 | 4,054,556 | 702,488 | 93,537 | $17.7610 | — |
