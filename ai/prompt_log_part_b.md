# Prompt log - Part B (z5652591)

Dated entries, most recent first. Template: `ai/prompt_log_template.md`.

---

## 2026-08-14 - Reproducibility correction and crypto-gap investigation

### What I wanted
Make the reproducibility claim literal for the complete committed `results/`
tree, correct the stale post-Prompt-8 sentence in the QA report, and investigate
the crypto/reference Sharpe gap without changing the frozen model.

### What the agent produced
An actual build from a deleted `results/` directory generated exactly 21 files.
Comparing that manifest with `git ls-files results` identified six tracked-only
files: three obsolete per-variant fusion CSVs and three `.gitkeep` placeholders.
All six were removed; the current combined `fusion_returns.csv` is the sole
canonical variant return file. No clean-build output was absent from Git.
Two independent clean builds then matched by SHA-256 for all 21 generated
files, including figures and supporting tables, not merely the four marker
files.

The diagnostic printed all 36 equity and crypto rebalance dates and observation
counts, recomputed the ridge at every decision, verified the published crypto
return moments, and recorded the full findings in `report/QA_REPORT.md`.

### What was wrong or risky
The earlier reproducibility check proved only the four required CSV hashes and
did not compare the complete tracked result manifest. Consequently, it missed
orphaned files that a fresh checkout could retain after an in-place build but a
truly empty build would never create. The QA report also retained a sentence
written before Prompt 8 saying Git had not been initialised, even after the
private push occurred.

The requested full `pytest tests/` run initially could not start because
`pytest` was not declared in `requirements-dev.txt`. I added `pytest>=8,<10`,
kept it out of deployment requirements, and reran successfully: 8 tests passed.

The crypto Sharpe gap looked superficially like it might be caused by covariance
scaling. It is not: the ridge is exactly `1e-8` of average variance in every
equity and crypto window, the absolute floor never binds, crypto covariance is
better conditioned than equity covariance, and equal weight—where no covariance
is used—shows the gap too. The exact 252/365 calendars and expanding counts are
also correct. The underlying crypto moments reproduce at 0.2226734509% mean and
5.1994728333% daily standard deviation.

### What I changed and why
Only stale artifacts and documentation were changed; no return, window,
annualisation, optimiser, regularisation, or fusion parameter changed. The
remaining lecture difference is documented as unexplained rather than tuned
away. GitHub identity was checked read-only: `RUOYUNWU-ui/desktop-tutorial`,
private, default branch `main`. Repository renaming and visibility were not
changed.

---

## 2026-08-13 - Codex Prompt 8: private release preparation

### What I wanted
Publish the reviewed project and its precomputed `results/` artifacts to the
student-confirmed GitHub target while keeping the repository private and
excluding raw data, local caches, and secrets.

### What the agent produced
The student chose the existing `RUOYUNWU-ui/desktop-tutorial` repository and
explicitly authorised replacement of its old contents. GitHub CLI verified the
authenticated account as `RUOYUNWU-ui`, repository visibility as `PRIVATE`,
and permission as `ADMIN`. The release uses one reviewed local `main` commit
and a protected replacement push tied to the previously observed remote commit,
so a concurrent remote change causes a stop instead of an accidental overwrite.

### What was wrong or risky
The first repository name proposed in the roadmap was not the repository the
student ultimately selected. The selected repository already contained a
tutorial commit and was initially observable anonymously, so pushing before
the student made it private would have violated the frozen deployment rule.
The first GitHub CLI download was also a standalone executable, not a graphical
app; double-clicking it only displayed a command-line explanation. I used its
explicit local path, required browser authentication, and re-checked visibility
before any write.

### What I changed and why
No model result was changed. Release housekeeping removes regenerated Python
caches, repeats the official checker and raw-data/secret gates, and commits the
entire confirmed project scope including `results/`. The agent does not connect
Streamlit Cloud and does not make the repository public; both remain student
actions.

---

## 2026-08-13 - Codex Prompt 7: final QA and submission scan

### What I wanted
Prove the project is reproducible, run real-data acceptance tests, compare the
fund results only directionally with the Week 10 worked example, run the
official hand-in checker, and remove caches/local clutter without touching the
frozen data loader or fitting parameters to the reference result.

### What the agent produced
- Repeated the clean rebuild test. The four core marker/app CSVs reproduced
  exactly, including row counts and SHA-256 hashes.
- Passed the smoke, all-12-fund no-look-ahead, sentiment, and fusion real-data
  tests. The tests explicitly cover weight timing, full investment,
  non-negativity, distinct optimisers, no-news handling, signal lagging, and
  lambda-zero equivalence.
- Added `tests/test_streamlit_app.py` so the five-page and invalid-allocation
  checks remain reproducible rather than existing only as a temporary QA run.
- Read and visually checked the Week 10 worked-example pages, then wrote the
  actual-versus-reference comparison to `report/QA_REPORT.md`.
- Removed generated Python caches, the copied IDE folder, and temporary PDF
  inspection files. Extended `.gitignore` for `.pytest_cache/`, `.idea/`, and
  `tmp/`.
- Ran the official checker: 22 checks passed, zero failures, one report
  reminder.

### What was wrong or risky
The first smoke/real-data invocation ran inside a network-restricted sandbox.
The smoke script catches data errors by design, so it printed a skip message
while still returning status zero; the real-data test then failed loudly on
the same connection restriction. Treating the smoke exit code alone as proof
would have been misleading. I reran with explicit temporary access to the
course's public ZIP and obtained `data load OK` plus all real-data passes.

The actual crypto Sharpe ratios are materially below the Week 10 worked
example, and crypto does not beat equity for all four methods. This is a real
sanity-check flag, not something to hide. The combined and equity results are
mostly close to the reference, minimum variance is lowest-volatility in every
family, and every timing/annualisation/constraint test passes. I therefore did
not reverse-engineer weights or parameters to force the desired ranking.

The hand-in checker still warns that `report/report.pdf` is absent. I did not
manufacture the student's economic interpretation: the brief explicitly says
that analysis must be in the student's own words.

### What I changed and why
Only housekeeping and documentation changed during QA. Model choices and
numeric parameters were left unchanged. Git was not initialised and nothing
was pushed, because the prompt makes those actions conditional on explicit
student confirmation.

---

## 2026-08-13 - Codex Prompts 5-6: reproducible artifacts and five-page app

### What I wanted
Create one official end-to-end build that writes the four exact marker/app
CSVs, all required exhibits and fact-sheet data, then replace the starter app
with a five-page investor journey that reads only those precomputed artifacts.

### What the assistant produced
`scripts/run_part_b.py` now rebuilds the Part A foundation, all 12 funds, both
sentiment models, fixed fusion variants, current holdings, a backtest audit,
manual lexicon review files, a market-wide 0-100 context index and seven
self-contained exhibits. It writes 10,392 fund-return rows, 17,280 fund-weight
rows, 20,120 sector-model sentiment rows, 12 performance rows, 480 current
holdings rows and 2,256 fusion-return rows. `streamlit_app.py` provides Home,
Fund Comparison, Fund Fact Sheet, Allocation Builder and Sentiment Analytics.

### What was wrong or risky
Visual QA found the performance-table fund-name column clipping longer labels;
the minimum-variance equity and combined drawdown series also overlap almost
exactly, making one line hard to see. The first server smoke-test wrapper used
a PowerShell process-launch path that failed because the host environment
contained duplicate case-insensitive Path/PATH keys; the app itself had not
started in that attempt. A second wrapper reached the health endpoint but its
unsupported process-kill overload caused only the wrapper to time out.

### What I changed and why
The first table column was widened and the overlapping combined drawdown line
made dashed without changing data. App verification was separated from wrapper
behaviour: Streamlit's AppTest opened all five pages with zero exceptions, and
an intentionally invalid allocation (76.67%) produced the required warning
rather than a crash. A real local Streamlit health request returned HTTP 200
and body `ok`; no listener remained afterward. Static search confirmed the app
contains no nltk, data_access, raw-loader, optimiser, backtest or scoring call.

For reproducibility, every generated file under `results/` except `.gitkeep`
was removed after validating the resolved target path, and the official script
was rerun from zero outputs. All four core CSVs matched the first build exactly
by both row count and SHA-256: fund_returns 10,392; fund_weights 17,280;
sector_sentiment_index 20,120; performance_metrics 12.

---

## 2026-08-13 - Codex Prompt 4: lag-safe sentiment fusion

### What I wanted
Apply the course formula to the minimum-variance equity fund using a sector
signal that is at least one trading day old, verify `lambda=0` exactly matches
the base, and retain fixed `lambda=+1/-1` results without selecting the winner
after seeing the OOS period.

### What the assistant produced
Codex implemented `apply_sentiment()` with the multiplicative rule, zero clip,
and equity-target renormalisation; crypto/non-equity weights remain unchanged.
It also implemented schedule-based return reconstruction and a fixed three-way
base/momentum/contrarian evaluator. A 60-trading-day rolling standardisation
window with 20 minimum observations was fixed before viewing fusion results,
as an untuned approximately one-quarter history. Missing signals produce no
tilt (`z=0`) while remaining flagged as unavailable.

### What was wrong or risky
The frozen text did not name a numerical z-score window. Treating it as a
parameter to search over the full OOS period would create the exact tuning
leakage the course warns about. Also, `rebalance_date` (base estimator close)
and `effective_date` (actual trade date) needed to be distinguished explicitly:
a Monday headline is valid for Tuesday's effective weights, not Monday's.

### What I changed and why
The 60/20 setting and both lambda signs were frozen without a search. The code
stores `sentiment_source_date` and asserts it is strictly earlier than
`effective_date`; the first source was 2021-01-04 and first tilted effective
date 2021-01-05. `lambda=0` passed exact row equality; all tilted rows remain
long-only and sum to one. Untuned real-data results were kept as observed:
base growth 1.2222, annual return 6.96%, vol 12.79%, Sharpe 0.590, max drawdown
-18.31%; momentum growth 1.2528, return 7.84%, vol 13.63%, Sharpe 0.622,
drawdown -20.38%; contrarian growth 1.3294, return 10.01%, vol 14.11%, Sharpe
0.747, drawdown -16.75%. These are results, not parameters used to re-pick a
sign or window.

---

## 2026-08-13 - Codex Prompt 3: plain and finance-enhanced VADER

### What I wanted
Build the plain-VADER baseline, a small explainable finance-lexicon extension,
equal-weight ticker sector indices, explicit no-news rows, a one-trading-day
lag, and a stratified manual-review sample without altering Part A's raw title
text.

### What the assistant produced
Codex implemented per-headline and ticker-day scoring, sector-index assembly,
VADER build-resource validation, a 24-term finance candidate table with scores
and rationales, and a plain-vs-enhanced comparison helper. The same scoring
path is used for both models; only the optional lexicon argument changes.
`tests/test_sentiment.py` verifies no-news/neutral separation and produces the
required real-data comparison and 5-headline-per-sector review sample.

### What was wrong or risky
The first real-data comparison assumed mapped `(date, ticker, sector, title)`
was unique. It is not: headlines were correctly deduplicated on original
publication date in Part A, but distinct weekend/holiday observations can map
to the same trading day and share the same mapped key. Re-deduplicating would
have thrown away valid observations.

### What I changed and why
Each exploded title now receives a stable `headline_id`, used only to align its
plain and enhanced scores. No mapped row is deleted. Real-data checks then
passed: 2,847 original duplicates removed, 6 post-calendar rows removed,
37,962 headline-panel groups, all 10 sectors, and 456 explicit sector-model
no-news rows. Plain VADER's headline neutral rate was 49.573657%; the enhanced
candidate lexicon reduced it to 47.809031% (-1.7646 percentage points). The
manual-review CSV has exactly 50 rows (5 per sector). The lexicon remains marked
"AI candidate - student review required" rather than being presented as a
completed human judgement.

---

## 2026-08-13 - Codex Prompt 2: 12-fund walk-forward OOS engine

### What I wanted
Implement the frozen 3 asset families x 4 methods matrix in
`src/portfolios.py`, with expanding-window monthly re-estimation, weights
effective on the next trading day, explicit 252/365 conventions, no exposure
caps, and machine-checkable no-look-ahead evidence.

### What the assistant produced
Codex implemented `performance_metrics()` and `oos_backtest()` for equal
weight, minimum variance, maximum Sharpe and risk parity. The result retains
`rebalance_date`, `effective_date`, and `estimation_end`, and returns daily OOS
returns, growth of one dollar, drawdown, long-format weights, audit rows,
turnover and the frozen spec. It also added `tests/test_no_lookahead.py`, with
synthetic and hosted-real-data verification modes.

### What was wrong or risky
Two issues were found by running the tests rather than trusting the draft.
First, the initial risk-parity auxiliary variable was incorrectly normalised
to sum to one before minimising the log-barrier risk-budgeting objective; this
caused an L-BFGS-B line-search failure. Second, the first monthly schedule was
initially formed by grouping only the post-window eligible tail, which made
2020-12-31 look like December's "first" trading date and produced 37 instead
of the expected 36 rebalances.

### What I changed and why
Risk parity now starts at the natural KKT scale
`sqrt(risk_budget / asset_variance)` and fails loudly if optimisation does not
converge. Monthly dates are now determined from the full trading calendar and
then filtered for estimation-window eligibility. The real-data rerun passed:
all 12 funds have 36 rebalances; equity/combined first OOS date is 2021-01-05,
crypto first OOS date is 2021-01-02; maximum weight-sum error is at most
4.44e-16; all weights are non-negative; every estimation end precedes its
effective date; and all six method pairs within every asset family have
different weight matrices (smallest reported maximum absolute difference was
0.018578, combined equal-weight vs risk-parity).

---

## 2026-08-13 - Correct frozen spec against the course's own reference solution

### What I wanted
Before writing (or generating, via Codex) any Station 3 code, check my
already-frozen `report/OUTLINE.md` backtest spec against
`week10_revision_fins5545.pdf` - the course's own "Agentic Coding and
Revision" lecture, which walks through a complete worked reference
implementation ("Overfit Capital") on the identical 2020-2023 dataset. I
asked Claude Code to read it and tell me where my spec disagreed.

### What the assistant produced
Two real disagreements, not just style differences:
1. My fund matrix was 3 asset families x 3 methods (Equal-Weight,
   Minimum-Variance, Risk Parity), with Maximum-Sharpe/tangency parked as an
   optional "stretch" method. The reference lecture builds all 4 methods
   (adding Maximum-Sharpe) x 3 universes = 12 funds as its *baseline*, with
   exact optimisation formulas given on slide 9. Since the lecture is public
   course material, an AI prompt can already reproduce a 3-method version
   trivially - shipping only 3 would read as *below* the demonstrated
   baseline, not as innovation.
2. My spec had TBD single-asset (20%) and combined-fund crypto (30%) weight
   caps, picked by me as a sensible-sounding default with no real evidence
   behind the specific numbers. The reference runs fully unconstrained and
   explicitly reports the resulting concentration as a finding (minimum-
   variance settling near 34% healthcare / near-zero crypto, "because
   minimising variance avoids the most volatile assets") - the concentration
   *is* the result to explain, not something to cap away by construction.

### What was wrong or risky
If I had briefed Codex to build the 3-method, capped version without ever
checking this lecture, I would have shipped a materially weaker "baseline"
than the one the marker demonstrated in their own revision session, and
hidden the exact concentration pattern the reference treats as a key
economic finding - not a coding bug, but a scope/design mistake that AI
would not have caught on its own since neither version is "wrong code."

### What I changed and why
Updated `report/OUTLINE.md`: fund matrix now 3x4=12 (added Maximum-Sharpe,
with its formula, to the required set, not stretch); removed the two TBD
caps and switched the baseline default to unconstrained long-only/fully-
invested, matching the reference, with a capped/constrained variant kept
available as an optional *labelled* extra sensitivity check rather than the
default. Also replaced my vague "bounded +-20% tilt" fusion description with
the reference's own precise formula (rolling z-score of lagged sentiment,
`w_tilde = w_base * (1 + lambda * z)`, clip-and-renormalise), and added the
reference's discovery-window/holdout-window tuning discipline (it shows a
tuned tilt scoring 0.84 in the window it was chosen on and 0.08 on the next
untouched year - exactly the overfitting trap the brief and my own earlier
`CLAUDE.md` rule already warned against, now with a concrete methodology to
follow instead of just "don't tune to the test period"). Left the Codex
prompt pack (`projectB_codex_prompts.md`, kept outside the submitted project
folder, in my own scratch space) to be rewritten against this corrected spec
before I hand any of it to Codex.

---

## 2026-08-13 - Project setup: port Part A modules, freeze backtest spec

### What I wanted
Stand up the Part B project from `projectB_starter.zip` (already unzipped into
this folder), reuse the parts of my completed Part A project that Part B is
allowed to reuse (per the brief's "Academic integrity" clause and my own
`PROJECT_B_ROADMAP.md`), and freeze the backtest/model assumptions before
writing any Station 3 code.

### Prompt(s)
Asked Claude Code to (1) implement "step 1" of the roadmap now that the
`z5652591_projectB` folder existed, using my own completed Part A project as
the source for reusable modules, and (2) cross-check the roadmap against the
official `project_brief_FINS5545.pdf` and `project_overview.pdf` before acting.

### What the assistant produced
- Read the official brief PDF and compared it against my own
  `PROJECT_B_ROADMAP.md`; confirmed no conflicts (required filenames, fund
  matrix, backtest rules, report structure, `check_handin.py` behaviour all
  matched). Flagged one folder-path difference (`fins-agent/fins2026/...`
  from the brief vs. my flat `FINS5545/z5652591_projectB` layout) as worth a
  sanity check, not a fix, since Part A was already submitted that way.
- Extracted my completed `z5652591_projectA.zip` and diffed
  `src/data_access.py` against the Part B starter's copy - byte-identical, so
  `etl.py`, `calendar_merge.py`, and `features.py` are safe to port unchanged
  (same interface, same frozen data source).
- Copied `calendar_merge.py`, `plot_style.py`, `innovation.py` (new files) and
  overwrote the stub `etl.py` and `features.py` with my completed Part A
  versions. Did **not** touch `src/data_access.py` (kept the Part B starter's
  copy, per the roadmap's explicit warning not to overwrite it).
- Installed `requirements.txt` + `requirements-dev.txt` (only `nltk` was
  missing locally) and ran `tests/test_smoke.py` - passed, data loads.
- Ran an end-to-end check of every ported module
  (`etl` -> `calendar_merge` -> `features` -> `plot_style` -> `innovation`)
  against the live hosted data inside this project (not assumed numbers).
- Drafted `CLAUDE.md` and `AGENTS.md` (both were still the unedited
  placeholder - `check_handin.py` fails until at least one is replaced).
- Added a "Backtest & model assumptions (fixed before coding)" section to
  `report/OUTLINE.md`: fund matrix (3 asset families x 3 methods), 252/365
  estimation windows, monthly rebalance, long-only/fully-invested, rf=0,
  costs=0, 252 vs 365 annualisation, sentiment lag >= 1 trading day, fusion
  scope (equity-only, bounded, renormalised), and an explicit rule that Part
  A's full-sample attention-volatility correlation (0.21) may only motivate a
  hypothesis, never backfill historical weights.

### What was wrong or risky
None of the ported code needed correction - the end-to-end check reproduced
Part A's exact published numbers on the first run:
- equities clean: 50,300 rows, 0 duplicates, 192 outlier candidates
- crypto clean: 14,610 rows, 10 rows dropped (post-2023-12-31), 60 outliers
- combined return panel: 60,360 rows
- news: 146,830 rows after dropping 2,847 duplicates and 6 unmappable rows
- headline panel: 37,962 (trading_day, ticker, sector) rows

This matched `PROJECT_A_COMPLETE_DOCUMENTATION.md` exactly, so no correction
was needed here - the risk this step was actually guarding against (silently
reusing a *different* or *stale* version of the Part A logic) did not
materialise, but it was verified rather than assumed.

One real risk I did have to catch: my own initial framing conflated "copy
Part A's report/results" with "copy Part A's *code*" - the brief and roadmap
both only permit reusing the latter; full-sample Part A statistics (e.g. the
attention-volatility correlation) must not feed OOS weights. That rule is now
written into both `CLAUDE.md`/`AGENTS.md` and `report/OUTLINE.md` so it isn't
relitigated later under results pressure.

### What I changed and why
No code changes needed beyond the port itself. Two placeholders that are
genuinely unresolved and must not be silently defaulted: the single-asset
weight cap and the combined-fund crypto-exposure cap, both left as `TBD` in
`report/OUTLINE.md` to be set explicitly (and recorded here) when
`src/portfolios.py` is drafted, rather than picked implicitly by whatever the
optimiser happens to do.
