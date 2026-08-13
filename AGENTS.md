# AGENTS.md - project instructions for Codex (and other agent tools)

Claude Code is the primary assistant on this Part B project; `CLAUDE.md` is the
canonical, fuller instruction file - read it first. This file exists so any
Codex (or other AGENTS.md-reading) session follows the same rules if I use one,
and so the AI-workflow record is honest about every tool touching this folder.
Read `PROJECT_BRIEF.md` and `context/` before doing anything else.

## What this project is

Part B (Stations 3-4 of the Data Factory Floor): out-of-sample systematic funds
(equity, crypto, combined), a standalone sector news-sentiment index, a
sentiment-fusion extension, and a Streamlit app, built on my own completed
Part A data foundation (`z5652591_projectA`).

## Rules that apply regardless of which tool is used

- `src/data_access.py` is provided and frozen - never edit it.
- No look-ahead in any backtest: weights use only data strictly before the date
  they are first applied; sentiment is lagged at least 1 trading day.
- Exact required output filenames: `results/data/fund_returns.csv`,
  `results/data/fund_weights.csv`, `results/data/sector_sentiment_index.csv`,
  `results/tables/performance_metrics.csv`.
- The frozen backtest/model spec lives in `report/OUTLINE.md` under "Backtest &
  model assumptions" - do not change it after seeing results without recording
  why in `ai/prompt_log_part_b.md`.
- `scripts/run_part_b.py` is the single reproducible entry point; the deployed
  app only reads `results/`, never recomputes.

## How I check and correct output

Every prompt that produces code, numbers, or a design decision I had to correct
gets a dated entry in `ai/prompt_log_part_b.md` (template:
`ai/prompt_log_template.md`), regardless of which assistant produced it.
