# Project B completion matrix

Last audited: 2026-08-14

**Proved** means that the current repository contains direct evidence and the
relevant command or manual check has passed. **External hand-in action** means
that the project is ready but the action depends on the student's authenticated
Streamlit or Moodle session.

| Scope | Requirement | Current evidence | Status |
|---|---|---|---|
| Foundation | Reuse verified Part A modules without changing the frozen loader | `results/tables/foundation_reproduction_audit.csv`; `src/data_access.py` remains byte-identical | **Proved** |
| Funds | 3 universes x 4 methods = 12 funds | `results/tables/performance_metrics.csv` | **Proved** |
| Backtest | Expanding-window OOS design; next-day effective weights; 252/365 conventions | `src/portfolios.py`; `results/tables/backtest_audit.csv`; real-data no-look-ahead test | **Proved** |
| Implementation | Holdings drift between monthly rebalances; turnover is pre-trade to target | `pre_trade_weight` and `turnover` in `fund_weights.csv`; `tests/test_robustness.py` | **Proved** |
| Constraints | Long-only, fully invested, 36 decisions per fund, methods distinct | Real-data audit in `tests/test_no_lookahead.py --real` | **Proved** |
| Sentiment | Plain and finance-enhanced VADER; ten-sector lagged index | `src/sentiment.py`; `sector_sentiment_index.csv`; `sentiment_model_comparison.csv` | **Proved** |
| Human review | 50 headlines and 24 finance terms completed and preserved across clean builds | `report/sentiment_manual_review_annotations.json`; validation and lexicon CSVs | **Proved** |
| Fusion | Fixed 60/20 standardisation and lambda 0/+1/-1; lambda-zero identity | `src/fusion.py`; `tests/test_fusion.py`; fusion result files | **Proved** |
| Innovation | Ledoit-Wolf shrinkage and 0/10/25/50/100 bps cost sensitivity | `src/robustness.py`; comparison tables and Figures A7-A8 | **Proved** |
| Reproducibility | One official build recreates the final result manifest | `scripts/run_part_b.py`; 28 generated files: 7 data, 9 figures, 12 tables | **Proved** |
| App | Six-page investor journey reads only precomputed artifacts | `streamlit_app.py`; `tests/test_streamlit_app.py` | **Proved locally** |
| Report | Final Word/PDF, Harvard references, required tables and Figures A1-A8 interpreted | `report/report.docx`; `report/report.pdf`; 14-page visual QA | **Proved** |
| AI workflow | Project instructions and teacher-format prompt log | `AGENTS.md`; `CLAUDE.md`; `ai/prompt_log_part_b.md` | **Proved** |
| GitHub | Public repository on `main` | `https://github.com/RUOYUNWU-ui/z5652591_projectB` | **Proved** |
| Streamlit | Public app opens from the public repository | Live URL must be deployed/confirmed in the student's Streamlit session | **External hand-in action** |
| Moodle | Zip, public repo URL and live app URL submitted | Final zip is prepared locally; Moodle upload remains | **External hand-in action** |

## Remaining external hand-in actions

1. Deploy or confirm the Streamlit Community Cloud app from
   `RUOYUNWU-ui/z5652591_projectB`, branch `main`, entrypoint
   `streamlit_app.py`.
2. Open the live URL in a logged-out browser and record it in the Moodle
   submission.
3. Upload the final zip together with the public repository and live app URLs.

These account-level actions do not require further model, report or code changes
unless the live deployment reveals an environment-specific error.
