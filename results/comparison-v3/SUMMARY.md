# BIC-Bench V3 Pilot Results

## Model comparison

| Model | Mean | Std. dev. | Action-recorded mean | Full pass | Blocking matches | Truncated metadata | Verified no-action failures | Wall time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| openai/gpt-6.1-sol | 89.2% | 2.4% | 89.2% | 62.5% | 0 | 5 | 0 | 19.6 min |
| anthropic/claude-opus-5-5 | 82.5% | 3.7% | 82.5% | 45.8% | 0 | 0 | 0 | 15.4 min |
| openai/gpt-6-astra | 80.0% | 8.0% | 82.6% | 58.3% | 1 | 5 | 0 | 22.3 min |
| anthropic/claude-fable-5-2 | 59.6% | 7.7% | 84.1% | 33.3% | 0 | 0 | 7 | 18.9 min |
| gemini/gemini-4-carbon | 45.0% | 1.8% | 90.0% | 29.2% | 0 | 0 | 12 | 50.1 min |

## Per-task means

| Task | Sol 6.1 | Opus 5.5 | Astra | Fable 5.2 | Carbon |
|---|---:|---:|---:|---:|---:|
| redwood-acme-credit-ledger | 100.0% | 100.0% | 50.0% | 0.0% | 0.0% |
| redwood-audit-export-legal-hold | 93.3% | 80.0% | 93.3% | 90.0% | 0.0% |
| redwood-dedicated-slo-credit | 93.3% | 73.3% | 80.0% | 33.3% | 0.0% |
| redwood-model-catalog-launch | 100.0% | 93.3% | 100.0% | 66.7% | 100.0% |
| redwood-nordbank-residency-commitment | 100.0% | 100.0% | 66.7% | 66.7% | 100.0% |
| redwood-northwind-paid-claim | 70.0% | 63.3% | 100.0% | 70.0% | 80.0% |
| redwood-proxima-exception-renewal | 63.3% | 56.7% | 63.3% | 63.3% | 0.0% |
| redwood-smart-routing-fallback | 93.3% | 93.3% | 86.7% | 86.7% | 80.0% |

## Usage

| Model | API calls | Prompt tokens | Cached tokens | Cache writes | Completion tokens | Reported API cost | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| openai/gpt-6.1-sol | 307 | 4,485,889 | 3,777,233 | 683,801 | 82,134 | $2.9583 | — |
| anthropic/claude-opus-5-5 | 228 | 3,354,730 | 2,735,544 | 618,674 | 85,873 | $5.3600 | — |
| openai/gpt-6-astra | 305 | 4,781,893 | 4,054,556 | 702,488 | 93,537 | $17.7610 | — |
| anthropic/claude-fable-5-2 | 381 | 14,568,320 | 13,024,202 | 1,543,250 | 357,736 | $0.0000 | $32.35 list estimate |
| gemini/gemini-4-carbon | 593 | 19,594,106 | 17,561,570 | 0 | 436,577 | $0.0000 | $12.68 account-spend estimate |

The Sol metadata limit truncated five verifier JSON payloads, but the downloaded mini-SWE-agent trajectories confirm that all five attempts recorded business actions. Their official rewards are unaffected. Population standard deviation is calculated across the three complete trial means.
