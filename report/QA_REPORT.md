# Part B final QA report

Date: 2026-08-13

This file records reproducibility and submission checks. It is not a substitute
for the student's final `report.pdf` and contains no attempt to tune results to
the Week 10 worked example.

## Reproducibility

The official pipeline was run, all generated files under `results/` (except
`.gitkeep`) were removed, and the pipeline was run again. The row counts and
SHA-256 hashes were identical across the two runs:

| Output | Rows | SHA-256 (both runs) |
|---|---:|---|
| `results/data/fund_returns.csv` | 10,392 | `B40D79D4F05E0F2DBE96FD614376AD2153C63BB05E1FE96367334B000C35E6D8` |
| `results/data/fund_weights.csv` | 17,280 | `7314A174374B1D116B9B053D83FA5E4EDB5BBADE870A1218E93738A543BF7F60` |
| `results/data/sector_sentiment_index.csv` | 20,120 | `0EE9F1613A76F3047B8947A6535E040FC1F9E382770F55E205A599C79CBA6482` |
| `results/tables/performance_metrics.csv` | 12 | `EBC34A0CE738FF8F7B09792B27A45D8C4BEE931B9961BDF931D266149A2EE401` |

## Automated acceptance checks

- `tests/test_smoke.py`: PASS (`imports OK`; `data load OK`).
- `tests/test_no_lookahead.py --real`: PASS for all 12 funds. Every estimation
  end date is before its effective date; each family has 36 monthly
  rebalances; weights are non-negative and sum to one within floating-point
  tolerance; all four methods produce distinct weights.
- `tests/test_sentiment.py --real`: PASS. The pipeline derived 2,847 news
  duplicates, dropped 6 headlines beyond the calendar, preserved explicit
  no-news observations, and applied the one-trading-day lag.
- `tests/test_fusion.py --real`: PASS. Lambda zero exactly reproduces the base,
  tilted portfolios remain fully invested, and every used sentiment source
  date precedes its effective date.
- `tests/test_streamlit_app.py`: PASS. All five Streamlit pages were exercised
  with Streamlit's app test runner with no exceptions; the invalid-allocation
  state correctly blocks the simulation.

## Direction-only Week 10 comparison

The course values below were read from the Week 10 revision deck's worked
example. They are a sanity reference, not a target. Actual values were not
altered in response to this comparison.

| Family | Method | Course Sharpe | Actual Sharpe | Direction note |
|---|---|---:|---:|---|
| Equity | Equal weight | 0.85 | 0.847 | Very close |
| Equity | Minimum variance | 0.62 | 0.590 | Same order |
| Equity | Maximum Sharpe | 0.72 | 0.595 | Lower, plausible OOS result |
| Equity | Risk parity | 0.75 | 0.746 | Very close |
| Crypto | Equal weight | 0.99 | 0.768 | Materially lower |
| Crypto | Minimum variance | 1.17 | 0.656 | Materially lower |
| Crypto | Maximum Sharpe | 0.73 | 0.518 | Materially lower |
| Crypto | Risk parity | 1.02 | 0.782 | Materially lower |
| Combined | Equal weight | 0.76 | 0.770 | Very close |
| Combined | Minimum variance | 0.61 | 0.590 | Very close |
| Combined | Maximum Sharpe | 0.40 | 0.433 | Very close |
| Combined | Risk parity | 0.78 | 0.797 | Very close |

Three conclusions follow:

1. Minimum variance has the lowest volatility in every family (equity 0.128,
   crypto 0.643, combined 0.128), matching the course direction.
2. Combined Sharpe is lower than crypto for minimum variance and maximum
   Sharpe, but approximately equal for equal weight and risk parity. This is
   weaker than the course's general ordering but not a numerical failure.
3. Crypto is not clearly above equity for every method: it is higher for
   minimum variance and risk parity, but lower for equal weight and maximum
   Sharpe. This reversal is explicitly flagged. Calendar, annualisation,
   constraints, and no-look-ahead invariants passed, so no parameter was
   changed merely to match the example.

The untuned fusion also behaves plausibly: base Sharpe 0.590, momentum 0.622,
and contrarian 0.747. Both signs were reported; the stronger realised sign was
not retrospectively selected as a new model specification.

## Submission scan and hand-in check

- `__pycache__` directories: 0.
- `.pyc` files: 0.
- Raw `.parquet` or CSV outside `results/`: 0.
- Runtime absolute-path matches in Python/TOML/text files: 0.
- Suspected secret matches outside results: 0.
- The only pre-existing documentation path match is a generic Windows
  placeholder in the provided data guide, not a machine-specific runtime path.
- `.gitignore` covers Python caches, virtual environments, IDE metadata,
  local temporary files, raw data, `.env`, and Streamlit secrets.

Full hand-in checker output:

```text
22 checks passed.
1 reminder(s):
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

No `[FAIL]` remains. The warning is intentionally unresolved because the brief
requires the written analysis and economic interpretation to be the student's
own words. Git was not initialised and nothing was pushed or made public,
because the student has not explicitly authorised those actions.
