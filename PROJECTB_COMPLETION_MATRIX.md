# Project B completion matrix

Last audited: 2026-08-13

Status meanings: **proved** means the current project contains direct evidence
and the relevant command has passed; **waiting for student** means the prompt
explicitly prohibits the agent from proceeding without confirmation or requires
the student's own writing/login.

| Scope | Requirement | Current evidence | Status |
|---|---|---|---|
| Foundation | Reuse the verified Part A ETL, calendar merge, features, style and innovation modules without changing the frozen loader | `src/` modules; `results/tables/foundation_reproduction_audit.csv`; `src/data_access.py` retains the provided frozen header | **Proved** |
| Prompt 2 | 3 families x 4 methods = 12 funds | `results/tables/performance_metrics.csv` has 12 unique funds | **Proved** |
| Prompt 2 | Expanding-window OOS backtest with next-day effective weights | `src/portfolios.py`; `results/tables/backtest_audit.csv`; `tests/test_no_lookahead.py --real` passed | **Proved** |
| Prompt 2 | Correct initial windows, calendars and annualisation | First OOS: equity/combined 2021-01-05, crypto 2021-01-02; 36 rebalances each; 252/365 settings returned in the backtest specification | **Proved** |
| Prompt 2 | Long-only, fully invested, no hand-coded caps; methods distinct | Real-data test reports minimum weight >= 0, maximum weight-sum error <= 4.441e-16, and all pairwise method differences > 1e-6 | **Proved** |
| Prompt 3 | Plain VADER and documented finance-lexicon extension | `src/sentiment.py`; `finance_lexicon_candidates.csv`; `sentiment_model_comparison.csv` | **Proved** |
| Prompt 3 | Preserve raw headline text and distinguish no news from neutral news | Headline scoring retains raw titles; `news_available` is explicit; real test reports 456 no-news sector/model rows | **Proved** |
| Prompt 3 | Ten sectors, one-day lag, enhanced neutral rate lower, 5 headlines per sector review | 10 sectors; 20,120 index rows; 49.573657% plain vs 47.809031% enhanced; 50-row review sample | **Proved** |
| Prompt 4 | Exact multiplicative sentiment tilt, clipping and renormalisation | `src/fusion.py`; `tests/test_fusion.py` | **Proved** |
| Prompt 4 | No look-ahead and lambda zero identity | Every used source date is before its effective date; lambda zero is row-for-row identical | **Proved** |
| Prompt 4 | Keep untuned +1 and -1 results, regardless of outcome | Base/momentum/contrarian Sharpe = 0.590/0.622/0.747; all three result series are saved | **Proved** |
| Prompt 5 | One official end-to-end build from hosted data | `scripts/run_part_b.py` | **Proved** |
| Prompt 5 | Four exact marker/app CSV names and schemas | `fund_returns.csv`, `fund_weights.csv`, `sector_sentiment_index.csv`, `performance_metrics.csv`; schemas checked by build and QA | **Proved** |
| Prompt 5 | Reproducibility after deleting results | Two independent clean builds produced exactly the same 21 paths and identical SHA-256 hashes for all 21 files; see `report/QA_REPORT.md` | **Proved** |
| Prompt 5 | Required self-contained exhibits with a custom, non-default palette | Seven PNG exhibits under `results/figures/`; visually inspected | **Proved** |
| Prompt 6 | Five-page investor journey reading precomputed artifacts only | `streamlit_app.py`; no raw loader, NLTK, scoring or optimiser references | **Proved** |
| Prompt 6 | Every page opens and invalid allocation is handled | Durable test in `tests/test_streamlit_app.py` passes all five pages and the non-100% guard | **Proved** |
| Prompt 7 | Two-run comparison, real tests, Week 10 direction check, checker and security scan | `report/QA_REPORT.md`; 22 checker passes, zero failures; no caches/raw data/secrets/runtime absolute paths | **Proved** |
| Prompt 7 | Local Git commit only if explicitly confirmed | Student explicitly authorised local initialisation and commit on 2026-08-13; this release is the reviewed project snapshot | **Proved by release commit** |
| Prompt 8 | Confirm repository target before using it | Student explicitly authorised replacing `RUOYUNWU-ui/desktop-tutorial`; GitHub CLI verified `PRIVATE` visibility and `ADMIN` permission | **Proved** |
| Prompt 8 | Push results but no raw data/secrets; provide private repository link | Pre-push scan has zero raw/bare data or secret matches; remote verification is performed immediately after the protected replacement push | **Release verification** |
| Prompt 8 | Browser-based Streamlit Cloud connection | Must be completed by the student using their own login after the private push | **Waiting for student** |
| Final course hand-in | Student-authored economic interpretation in `report/report.pdf` | `report/OUTLINE.md` and `report/QA_REPORT.md` provide evidence and structure; final prose/PDF absent | **Waiting for student** |
| Final course hand-in | Public repository and live public Streamlit URL at submission | Prompt 8 deliberately keeps the test repository private; publication is a later student action | **Waiting for student** |

## Remaining student-only gates

The Git/repository decision gates have been explicitly cleared. The remaining
student-only work is to author the final economic interpretation, deploy through
the student's own Streamlit Cloud browser session, and make the repository
public only at final hand-in after checking the live app in a logged-out browser.
