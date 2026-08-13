# Report outline (Part B)

Author your report in Word (`report.docx` is your editable source; this OUTLINE.md is
only a planning aid) and submit it as `report.pdf`. Max 10 pages of written narrative
(excluding appendix and references) - you may place the required exhibits in an
appendix. Suggested structure:

1. The funds and the backtest design.
2. Out-of-sample results and fund fact sheets.
3. The sentiment index.
4. The fusion extension and whether it adds value.
5. The app and the investor journey.
6. Critical reflection with three concrete recommendations.

Every figure and table must be self-contained (caption, labelled axes, units,
sample period) and referenced and interpreted in the text. The canonical list of
required exhibits is in PROJECT_BRIEF.md, Section 5.

## Backtest & model assumptions (fixed before coding)

Written down before `src/portfolios.py` / `src/sentiment.py` / `src/fusion.py`
were implemented, so results cannot quietly change the spec afterwards. Any
later change must be logged in `ai/prompt_log_part_b.md` with a reason.

**Amendment (2026-08-13):** revised after reading the course's own Week 10
"Agentic Coding and Revision" lecture, which walks through a complete worked
reference solution ("Overfit Capital") built on this exact 2020-2023 dataset.
Two changes below are corrections against that reference, not new ideas of my
own - logged in `ai/prompt_log_part_b.md`.

**Fund universe (required minimum: combined + 2 methods; target: 3x4 = 12 funds,
matching the course reference exactly)**

| Asset family | Equal Weight | Minimum Variance | Maximum Sharpe (Tangency) | Risk Parity |
|---|---|---|---|---|
| Equity-only | yes | yes | yes | yes |
| Crypto-only | yes | yes | yes | yes |
| Combined | yes | yes | yes | yes |

Maximum-Sharpe / mean-variance tangency moved from "stretch" to the core
matrix - the Week 10 slides use exactly these 4 methods x 3 universes = 12
funds as the course's own baseline, so building only 3 methods would be
*below* baseline, not innovation. Formulas (all long-only, fully invested,
$\mathbf{1}^\top w = 1$, $w \ge 0$), with $\mu$ = mean daily returns and
$\Sigma$ = covariance matrix, both estimated on the expanding window to date:

- Equal-weight: $w_i = 1/N$ (no estimation).
- Minimum-variance: $\min_w w^\top \Sigma w$.
- Maximum-Sharpe (tangency): $\max_w \dfrac{w^\top(\mu - r_f \mathbf{1})}{\sqrt{w^\top \Sigma w}}$, $r_f = 0$.
- Risk parity: solve for $w$ such that every asset's risk contribution is
  equal, $RC_i = \dfrac{w_i (\Sigma w)_i}{w^\top \Sigma w} = \dfrac{1}{N}$.

Because AI can now reproduce this exact 12-fund matrix directly from the
lecture, it is the *baseline*, not the innovation - see "innovation
candidates" below for what still needs to be genuinely mine.

**Windows and rebalancing**

- Expanding window (not fixed rolling): each month's estimation window is all
  data from the start of the sample up to that rebalance date, growing over
  time - matches the course reference exactly ("Re-Training on an Expanding
  Window").
- Equity and combined funds: 252-trading-day initial estimation window,
  monthly rebalance (first trading day of each calendar month). On this
  dataset that puts the first live OOS date in expected in January 2021 and
  yields roughly 36 monthly rebalances through end of 2023 - matches the
  course reference's own numbers, useful as a sanity check on my own run.
- Crypto-only fund: 365-calendar-day initial estimation window, monthly
  rebalance, on crypto's own daily calendar.
- New weights are estimated using only data up to and including the rebalance
  date, and take effect from the next trading day - the first OOS return date
  is therefore strictly after the initial estimation window, never the first
  date in the sample.
- After a target becomes effective, holdings drift with each asset's realised
  return until the next monthly rebalance. Rebalance turnover is measured from
  the drifted pre-trade portfolio to the new target,
  $0.5\sum_i|w^{target}_{i,t}-w^{pre}_{i,t}|$; initial funding is not counted.
- Combined fund trades on the equity calendar (Part A's
  `combine_equity_crypto_returns` convention); weekend-only crypto moves are
  not separately tradeable.

**Constraints and baseline assumptions**

- Long-only, fully invested: weights are non-negative and sum to 1.
- **No single-asset or crypto-exposure cap in the baseline funds** - reversed
  from the earlier TBD default (20%/30%). The course reference runs
  unconstrained and reports the resulting concentration as a finding (e.g.
  combined minimum-variance settles near 34% healthcare, near-zero crypto -
  that concentration *is* the economic story: minimising variance avoids the
  most volatile assets). Adding caps un-asked would make my baseline
  non-comparable to the reference and would hide a result I should instead
  explain. A constrained/capped variant is still available as an optional,
  clearly-labelled extra sensitivity check later, not the default.
- Risk-free rate = 0 for Sharpe (stated, per brief Section 5, matches
  reference).
- Transaction costs = 0 for the baseline (stated, per brief Section 5).
  Turnover reported as a metric; the course reference shows a transaction-cost
  sensitivity curve (net Sharpe vs. cost in bps per trade at 0/10/25/50/100)
  as a worked example of a cheap, well-received extension - candidate for the
  "second innovation" slot if time allows, not required.

**Annualisation**

- Equity and combined funds: 252 trading days/year.
- Crypto-only fund: 365 calendar days/year.

**Sentiment / fusion**

- Sentiment scored per headline with VADER on the Part A mapped headline
  panel (raw casing/punctuation preserved), aggregated to ticker-day, then
  equal-weighted across tickers within a sector for the daily sector index.
- Ticker-days with no headlines: flagged with a `news_available` indicator
  rather than silently treated as neutral (0), so "no news" and "neutral
  news" stay distinguishable in the index and in fusion.
- Sentiment signal lagged at least 1 trading day (`shift(1)`) before it can
  affect any fund weight - a Saturday/Monday headline (mapped to Monday) is
  first usable for Tuesday's rebalance/trade, never Monday's.
- Fusion (`apply_sentiment`) tilts equity weights only, then renormalises to
  keep long-only and fully-invested. This is explicitly a **sector-level
  tilt**, because the available index is sector-level: each ticker inherits
  its sector's lagged score. Standardise each sector's lagged sentiment into a
  rolling z-score using only information available before the trade date
  ($z_{g,t} = (s_{g,t}-\bar s_{g,t})/\sigma^s_{g,t}$), then for ticker $i$ in
  sector $g(i)$ set $\tilde w_{i,t} = w_i^{base}(1+\lambda z_{g(i),t})$, clip negatives to 0
  and renormalise ($w_{i,t} = \max(\tilde w_{i,t},0) / \sum_j \max(\tilde
  w_{j,t},0)$). $\lambda>0$ is a momentum tilt (more weight to good-news
  sectors), $\lambda<0$ is contrarian, $\lambda=0$ reproduces the base fund
  exactly - useful as a self-check.
- Base fund for the fusion comparison: minimum-variance equity fund (matches
  the course reference's own worked example, so results are directly
  comparable to what was shown in the Week 10 lecture).
- If $\lambda$ (or the sentiment model/lexicon choice) is tuned rather than
  fixed by hand, tune only on an early sub-window of the OOS period (e.g.
  2021-2022 as a "discovery" window) and report the final result on a later,
  untouched holdout (e.g. 2023) - the course reference explicitly demonstrates
  that tuning against the *whole* OOS period can look great in-sample-to-the-
  tuning (Sharpe 0.84) and then collapse on new data (Sharpe 0.08). A hand-set,
  untuned $\lambda$ (e.g. +-1) evaluated once on the full OOS period is also an
  acceptable and simpler alternative - just do not do both (do not hand-set it
  *and* silently re-pick it after seeing which sign looks better).
- Part A's full-sample sector attention-volatility correlation (pooled 0.21)
  is motivation/hypothesis only - it must never be used to set or backfill
  historical weights, since it uses same-period (look-ahead) information.

**Innovation candidates (need at least one genuinely mine, beyond the 12-fund
baseline above)**

Primary: finance-lexicon-enhanced VADER sentiment tilt (already planned,
matches the brief's own named example). Backup / stretch list, taken from the
course's own "Ideas, Structured" and "Ideas Across the Project" slides, kept
here so a second extension can be picked quickly if time allows: covariance
shrinkage, a transaction-cost sensitivity curve, volatility targeting, an
equal-weight/minimum-variance blend, or a tail-aware (mean-CVaR) objective.
Pick at most one of these as a second extension - one well-executed extension
beats several shallow ones (brief, Section "What counts as innovation").

**Amendment (2026-08-14):** two closely related robustness extensions were
completed because both reuse the frozen backtest and answer distinct investor
questions without tuning: Ledoit-Wolf covariance shrinkage tests estimator
risk, while the fixed-bps transaction-cost curve tests implementation drag.
Both are reported separately from the canonical 12 funds; neither parameter or
baseline result was changed after viewing OOS performance.

**Correction (2026-08-14):** the earlier wording described the fusion as a
ticker-level z-score even though the implemented and available signal is the
sector sentiment index. The wording above now states the actual sector-level
tilt. The backtest implementation was also corrected to let holdings drift
between monthly target dates and to calculate turnover from pre-trade to target
weights; this is an implementation correction, not result-driven retuning.
