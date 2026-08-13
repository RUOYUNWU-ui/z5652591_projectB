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
own words. Git was subsequently initialised and committed, and commit
`fe7f83dbebf811f2959b9414999ce64cbb7cbbd0` was pushed to the private repository
`RUOYUNWU-ui/desktop-tutorial` at
<https://github.com/RUOYUNWU-ui/desktop-tutorial>. The repository was not made
public and Streamlit Cloud was not connected by the agent.

## Addendum — 2026-08-14

### Prompt 8 status correction

The earlier closing statement that Git had not been initialised was accurate
when the 2026-08-13 QA snapshot was first written, but became stale after the
student explicitly authorised Prompt 8. This addendum records that later event
rather than rewriting the sequence: the project became its own Git repository,
was committed on `main`, and replaced the contents of the confirmed private
repository above. A remote-tree audit found 64 blobs, including all four
required result CSVs, and zero raw Parquet files, CSVs outside `results/`,
secrets, `.pyc` files, or `__pycache__` paths.

### Literal clean-build results audit

The full tracked-results list was compared against an actual build from a
deleted `results/` directory. The clean pipeline creates exactly 21 files. Six
previously tracked files were not created:

- the obsolete split files `fusion_returns_base.csv`,
  `fusion_returns_momentum.csv`, and `fusion_returns_contrarian.csv`; their rows
  now live in the single canonical `fusion_returns.csv` with a `variant` column;
- `.gitkeep` in each of `results/data`, `results/tables`, and
  `results/figures`; these placeholders are unnecessary once the directories
  contain real generated artifacts.

All six were removed from the repository. There were no files produced by the
clean build that were missing from version control. A second clean build and
the final all-file hash comparison are recorded below.

The second clean build produced the same 21 paths and the same SHA-256 for
**every one of the 21 files**, including all seven PNG figures and every
supporting CSV. The four marker-required hashes remained:

| Required output | SHA-256 after final clean build |
|---|---|
| `fund_returns.csv` | `B40D79D4F05E0F2DBE96FD614376AD2153C63BB05E1FE96367334B000C35E6D8` |
| `fund_weights.csv` | `7314A174374B1D116B9B053D83FA5E4EDB5BBADE870A1218E93738A543BF7F60` |
| `sector_sentiment_index.csv` | `0EE9F1613A76F3047B8947A6535E040FC1F9E382770F55E205A599C79CBA6482` |
| `performance_metrics.csv` | `EBC34A0CE738FF8F7B09792B27A45D8C4BEE931B9961BDF931D266149A2EE401` |

The requested final validation then passed:

- `python -m pytest tests/ -q`: **8 passed**;
- `python tests/test_no_lookahead.py --real`: **PASS** for all 12 funds,
  including 36 rebalances per fund, strict estimation/effective-date ordering,
  non-negative fully invested weights, and distinct methods;
- `python scripts/check_handin.py`: rerun after cache cleanup, with its exact
  final output recorded at the end of this addendum.

The first attempt to run the full pytest suite exposed that `pytest` was not
declared in `requirements-dev.txt`. This was corrected with `pytest>=8,<10`,
installed only as a development/reproduction dependency; the lightweight
Streamlit deployment requirements were not changed.

### Crypto Sharpe-gap investigation (no retuning)

The 36 equity and crypto decision windows were reconstructed directly from the
clean return panels. The exact rebalance dates and expanding-window counts are:

| # | Equity date | Equity obs. | Crypto date | Crypto obs. |
|---:|---|---:|---|---:|
| 1 | 2021-01-04 | 253 | 2021-01-01 | 366 |
| 2 | 2021-02-01 | 272 | 2021-02-01 | 397 |
| 3 | 2021-03-01 | 291 | 2021-03-01 | 425 |
| 4 | 2021-04-01 | 314 | 2021-04-01 | 456 |
| 5 | 2021-05-03 | 335 | 2021-05-01 | 486 |
| 6 | 2021-06-01 | 355 | 2021-06-01 | 517 |
| 7 | 2021-07-01 | 377 | 2021-07-01 | 547 |
| 8 | 2021-08-02 | 398 | 2021-08-01 | 578 |
| 9 | 2021-09-01 | 420 | 2021-09-01 | 609 |
| 10 | 2021-10-01 | 441 | 2021-10-01 | 639 |
| 11 | 2021-11-01 | 462 | 2021-11-01 | 670 |
| 12 | 2021-12-01 | 483 | 2021-12-01 | 700 |
| 13 | 2022-01-03 | 505 | 2022-01-01 | 731 |
| 14 | 2022-02-01 | 525 | 2022-02-01 | 762 |
| 15 | 2022-03-01 | 544 | 2022-03-01 | 790 |
| 16 | 2022-04-01 | 567 | 2022-04-01 | 821 |
| 17 | 2022-05-02 | 587 | 2022-05-01 | 851 |
| 18 | 2022-06-01 | 608 | 2022-06-01 | 882 |
| 19 | 2022-07-01 | 629 | 2022-07-01 | 912 |
| 20 | 2022-08-01 | 649 | 2022-08-01 | 943 |
| 21 | 2022-09-01 | 672 | 2022-09-01 | 974 |
| 22 | 2022-10-03 | 693 | 2022-10-01 | 1,004 |
| 23 | 2022-11-01 | 714 | 2022-11-01 | 1,035 |
| 24 | 2022-12-01 | 735 | 2022-12-01 | 1,065 |
| 25 | 2023-01-03 | 756 | 2023-01-01 | 1,096 |
| 26 | 2023-02-01 | 776 | 2023-02-01 | 1,127 |
| 27 | 2023-03-01 | 795 | 2023-03-01 | 1,155 |
| 28 | 2023-04-03 | 818 | 2023-04-01 | 1,186 |
| 29 | 2023-05-01 | 837 | 2023-05-01 | 1,216 |
| 30 | 2023-06-01 | 859 | 2023-06-01 | 1,247 |
| 31 | 2023-07-03 | 880 | 2023-07-01 | 1,277 |
| 32 | 2023-08-01 | 900 | 2023-08-01 | 1,308 |
| 33 | 2023-09-01 | 923 | 2023-09-01 | 1,339 |
| 34 | 2023-10-02 | 943 | 2023-10-01 | 1,369 |
| 35 | 2023-11-01 | 965 | 2023-11-01 | 1,400 |
| 36 | 2023-12-01 | 986 | 2023-12-01 | 1,430 |

These dates are the first trading/calendar date of each month and the counts
grow exactly as expected under the frozen 252-day equity and 365-day crypto
specifications. Both families start trading on the following date, not on the
estimation date.

The covariance regularisation is scale-proportional. Across the 36 decisions,
equity's average annualised asset variance ranges from 0.135416 to 0.263260 and
its ridge from `1.354161e-09` to `2.632597e-09`; crypto's average variance
ranges from 0.999474 to 1.592800 and its ridge from `9.994737e-09` to
`1.592800e-08`. In every case, for both families, `ridge / average variance`
is exactly `1e-8`; the absolute `1e-12` floor binds zero times. Regularisation
therefore scales with crypto's larger variance rather than imposing a larger
relative penalty. Crypto's raw covariance condition numbers (64.77–89.57) are
also lower than equity's (358.76–691.05), so this diagnostic gives no evidence
of worse crypto covariance conditioning.

As an independent data check, the 14,600 ticker-day crypto returns have mean
0.2226734509% and sample standard deviation 5.1994728333%, matching the audited
Part A statistics. Finally, equal weight does not call the covariance or
optimiser at all, yet its crypto Sharpe (0.768) is also below the lecture's
0.99. The ridge cannot therefore explain the four-fund gap. No calendar,
window, annualisation, return-data, look-ahead, constraint, or covariance-scale
fault was found. The remaining difference from the lecture example is real but
unexplained—plausibly an unreported implementation/convention difference in
the worked example—and no model parameter was changed to chase it.

### Final hand-in checker output after correction

```text
22 checks passed.
1 reminder(s):
  [WARN] no report/report.pdf yet - author it in Word and export to PDF
All checks passed - ready to zip and deploy.
```

There are zero `[FAIL]` items. The sole warning remains a genuine student task,
not a reproducibility or code defect.

## Addendum - 2026-08-14: innovation extensions, report, and app integration

Two pre-specified robustness extensions were implemented without replacing or
retuning the canonical 12-fund baseline. First, minimum-variance and
maximum-Sharpe funds were rerun with Ledoit-Wolf covariance shrinkage estimated
inside each expanding window. The largest change was crypto minimum variance
(Sharpe +0.097); crypto maximum Sharpe changed +0.040, while the other four
comparisons ranged from -0.013 to +0.014. The result is mixed rather than a
universal improvement. Second, every baseline fund was evaluated at one-way
transaction costs of 0, 10, 25, 50, and 100 bps, charged on post-launch
rebalance turnover. At 50 bps, the largest Sharpe reductions were equity
maximum Sharpe (-0.040) and combined maximum Sharpe (-0.030), consistent with
their substantially higher turnover.

The extensions write `shrinkage_comparison.csv`,
`transaction_cost_sensitivity.csv`, and a separate shrinkage return history.
The Streamlit app now has a sixth precomputed-results page, `Robustness Lab`,
that exposes both experiments without importing scikit-learn or recomputing a
backtest at runtime. The four marker-required baseline files retained their
previous SHA-256 hashes exactly.

A stratified 50-headline manual-review template and validator were added. The
student-label fields are intentionally blank: AI labels would not constitute
independent human validation. The validator refuses incomplete labels and,
after genuine student review, reports plain-versus-enhanced VADER agreement.

An editable 14-page report draft was generated as `report/report.docx`, with a
matching `report/report.pdf`. Pages 1-7 contain the narrative; pages 8-14 are
appendices and references. All 14 pages were rendered to PNG and visually
checked for clipping, table overflow, figure readability, headers, footers, and
page numbering. One incorrect cross-reference (`Figure A9`) was corrected to
`Figure A8`, then the document was regenerated and rechecked. The report is
clearly marked as an AI-assisted draft and does not claim the outstanding
manual review is complete.

### Final clean-build verification after the extensions

`results/` was deleted in full and recreated only by
`python scripts/run_part_b.py`. The clean run produced exactly 27 files: 7 app
data CSVs, 9 figures, and 11 report/audit tables. No committed result lies
outside that generated set. The four required hashes remained:

- `fund_returns.csv`: `B40D79D4F05E0F2DBE96FD614376AD2153C63BB05E1FE96367334B000C35E6D8`;
- `fund_weights.csv`: `7314A174374B1D116B9B053D83FA5E4EDB5BBADE870A1218E93738A543BF7F60`;
- `sector_sentiment_index.csv`: `0EE9F1613A76F3047B8947A6535E040FC1F9E382770F55E205A599C79CBA6482`;
- `performance_metrics.csv`: `EBC34A0CE738FF8F7B09792B27A45D8C4BEE931B9961BDF931D266149A2EE401`.

The expanded suite passed **10 tests**. The separate real-data no-look-ahead
test passed all 12 funds and 36 rebalances per fund. After deleting generated
Python caches, `scripts/check_handin.py` passed **23 checks with zero warnings
and zero failures**.

## Addendum - 2026-08-14: manual-review and turnover correction

This addendum supersedes only the implementation/result claims in the preceding
addendum; the earlier record is retained rather than rewritten. The student has
now completed all 50 headline labels and reviewed all 24 finance-lexicon terms.
`run_part_b.py` first preserves the human-only fields in
`report/sentiment_manual_review_annotations.json`, identified by headline ID and
title hash, then restores them into a fresh generated sample. A deliberate clean
test deleted the entire `results/` directory: the rebuild restored 50/50 complete
labels, regenerated the validation CSV, and retained 24/24 reviewed and accepted
lexicon decisions. Human agreement is 66% for plain VADER and 70% for enhanced
VADER; positive agreement rises from 66.7% to 80.0%, while negative agreement
remains 33.3%.

The backtest implementation was corrected from daily constant-target weights to
monthly target weights that drift with realised asset returns. At each effective
rebalance, turnover is now `0.5 * sum(abs(target - pre_trade))`; initial funding
is zero turnover. The same drift mechanics apply to fusion variants. This changes
baseline returns, weights, metrics, shrinkage comparisons and transaction-cost
curves, so the prior hash-preservation statement is no longer applicable. It is
an implementation correction, not a parameter or method change. For example,
equity equal-weight now has 2.77% mean monthly turnover and equity maximum-Sharpe
has 13.67%; equal-weight turnover is no longer incorrectly zero.

The clean rebuild now produces exactly 28 files: 7 data CSVs, 9 figures and 12
tables (the extra table is the completed manual-review validation). No previously
tracked file under `results/` is absent from a fresh build. The new required-file
SHA-256 values are:

- `fund_returns.csv`: `FEF0173069875F3ADE3A39F1B2B48DD07E251B69AB0AB68CB43C4B1F87ADD5B9`;
- `fund_weights.csv`: `A8816F630EF53D27FD3AC2290504AD792871DC0F7ED8934ECE0F7D4A6BEF5048`;
- `sector_sentiment_index.csv`: `0EE9F1613A76F3047B8947A6535E040FC1F9E382770F55E205A599C79CBA6482`;
- `performance_metrics.csv`: `AD0C051AE09320844F14853B90FB61B0D048B68C62CCD585E550EC3F3EFE2658`.

The report generator now describes the actual sector-level tilt and interprets
Figures A1-A8 in the narrative, including the completed human validation. The
14-page DOCX was regenerated, rendered page by page, and visually checked; the
matching PDF was replaced from that render. The full suite now passes **13
tests** in one command. Setting Matplotlib to the non-GUI Agg backend removed a
Windows/Python 3.14 teardown failure without skipping any app test. The separate
real-data audit again passed all 12 funds and 36 rebalances per fund. After cache
cleanup, `scripts/check_handin.py` passed **23 checks with zero warnings and zero
failures**. `src/data_access.py` remains byte-for-byte untouched.

## Addendum - 2026-08-14: final report and hand-in consistency

The student-edited report was checked against the Part B rubric and the supplied
UNSW cover reference. The cover was adapted for FINS5545 and an individual
submission; a required fusion before/after table was added; all Figures A1-A8
and Tables 1-5, A1 and B1 are referenced and interpreted in the narrative; and
the references use Harvard author-date form. The 14-page DOCX/PDF was rendered
page by page and checked for clipping, missing images, table overflow, headers,
footers and page numbering. The written narrative occupies seven pages and is
below the brief's ten-page maximum.

To protect the student's final manual edits, `scripts/build_report.py` now writes
`report/report_generated_draft.docx` instead of overwriting
`report/report.docx`. The README, submission checklist and completion matrix now
reflect the final 28-file build, completed 50-headline and 24-term reviews, six
app pages and public repository
`https://github.com/RUOYUNWU-ui/z5652591_projectB`. The only unverified course
deliverable is the browser-authenticated live Streamlit URL; it must be opened in
a logged-out browser and submitted with the public repository and Moodle zip.

## Addendum - 2026-08-14: public Streamlit deployment verified

The student completed deployment at
`https://z5652591projectb-carymh8kgzkfbrbzdhyjr7.streamlit.app/`. The public app
was then opened in a browser without an authenticated Streamlit account session.
The Home page loaded the expected 12-fund, three-family and four-method summary.
Each of the five remaining navigation choices was opened in turn: Fund
Comparison, Fund Fact Sheet, Allocation Builder, Sentiment Analytics and
Robustness Lab. Their expected headings and evidence appeared, and no application
alerts or exceptions were present. This closes the previously outstanding live
deployment item. Moodle upload remains an account-level submission action.
