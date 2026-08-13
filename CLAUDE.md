# CLAUDE.md - project instructions for Claude Code

My own instructions to Claude Code for FINS5545 Project B (z5652591). Claude Code
is the primary assistant on Part B (Part A used Codex for first drafts and Claude
Code for review; see `ai/prompt_log_part_b.md` for the actual, dated record of what
was asked and what I changed). Read `PROJECT_BRIEF.md` and `context/` first.

## What this project is

Part B (Stations 3-4 of the Data Factory Floor): turn the Part A data foundation
into out-of-sample systematic funds (equity, crypto, combined), a standalone
sector news-sentiment index, a sentiment-fusion extension, and a Streamlit app -
see `PROJECT_A_COMPLETE_DOCUMENTATION.md`-equivalent context and
`context/project_context.md` for what Part A already delivered.

## Conventions and folder layout

- `src/data_access.py` - PROVIDED, frozen. Never edit it.
- `src/etl.py`, `src/calendar_merge.py`, `src/features.py`, `src/plot_style.py`,
  `src/innovation.py` - ported from my own completed Part A project
  (`z5652591_projectA`), unchanged. Verified on first run in this project to
  reproduce Part A's exact published numbers (50,300 clean equity rows, 192
  outlier candidates, 2,847 duplicate headlines removed, 37,962-row headline
  panel) - see the AI log entry for that check.
- `src/portfolios.py` - Station 3 optimisation + walk-forward OOS backtest
  (`oos_backtest()`, `performance_metrics()`). New code for Part B.
- `src/sentiment.py` - Station 3 sentiment model (`score_headlines()`,
  `sector_sentiment_index()`). New code for Part B.
- `src/fusion.py` - Station 3 sentiment-tilt fusion (`apply_sentiment()`). New
  code for Part B.
- `scripts/run_part_b.py` - the ONLY script that has to be run to reproduce every
  result and CSV under `results/`. Do not add a second script that duplicates it.
- `streamlit_app.py` - reads only precomputed `results/` CSVs. Never imports
  `nltk`, never calls the optimiser or the backtest at app runtime.

## Rules I want followed (frozen before writing portfolio/sentiment code)

See `report/OUTLINE.md`, "Backtest & model assumptions (fixed before coding)" for
the full frozen spec. The non-negotiable ones:

- No look-ahead: every OOS weight is computed from data strictly before the date
  it is first used; the first live backtest date is after the initial estimation
  window, not the first date in the data.
- Sentiment signal is lagged at least 1 trading day (`shift(1)` on the equity
  trading calendar) before it touches any fund weight.
- Equity/combined funds annualise with 252, crypto-only with 365.
- Sentiment fusion applies to the equity portion of a fund's weights only.
- Do not let Part A's full-sample results (e.g. the 0.21 pooled
  attention-volatility correlation) feed directly into historical weights -
  they may only motivate a hypothesis, tested here with proper OOS data.
- Exact required filenames: `results/data/fund_returns.csv`,
  `results/data/fund_weights.csv`, `results/data/sector_sentiment_index.csv`,
  `results/tables/performance_metrics.csv`.
- If a sentiment-augmented fund underperforms the base fund, report that
  honestly rather than tuning parameters against the OOS period until it wins.

## How I check and correct output

I run every script myself against real hosted data (not assumed numbers) and
check printed shapes/counts against what I expect before trusting them - for
example, that weights actually change across methods (the brief flags solver
scaling as a real risk: optimisers can silently stall on tiny daily-return
covariances). I keep a dated entry in `ai/prompt_log_part_b.md` for any prompt
that produced code, numbers, or a design decision I had to correct, using
`ai/prompt_log_template.md`.
