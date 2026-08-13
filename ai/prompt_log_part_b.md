# Prompt log - FINS5545 Project B (z5652591)

This curated log follows the five-field structure in the teacher-provided
`ai/prompt_log_template.md`. It records the main workflow in chronological
order: what I asked an AI assistant to do, what it produced, what I judged to
be wrong or risky, and what I changed after checking the course material,
source code, tests and generated evidence. It is not a transcript of every
minor conversation. My written economic interpretation and the two manual
sentiment reviews remain my own work.

## 1. Project setup - reuse Part A and freeze all assumptions before coding (13 August 2026)

### What I wanted

Build Part B on top of my completed Part A work, reusing only the modules
permitted by the project brief. Before writing portfolio or sentiment code, I
wanted every design assumption fixed in writing - estimation windows,
rebalance schedule, constraints, annualisation rules, sentiment lag and the
baseline treatment of transaction costs - so nothing would be tuned after
seeing results. I also wanted to confirm that the plan matched the official
brief and starter structure.

### Prompt(s)

> "Port over my Part A data loading, cleaning, calendar-merging, feature and
> plotting modules unchanged into this Part B project. Reuse only my own work
> and do not overwrite the provided `src/data_access.py`."

> "Read the official project brief and structure documents. Compare my plan
> against them line by line and flag mismatches in filenames, folder layout,
> fund matrix, rules and deliverables."

> "Write all frozen assumptions clearly in the outline: universes, methods,
> initial estimation windows, monthly rebalance rule, decision and effective
> dates, long-only and fully-invested constraints, zero risk-free rate, zero
> transaction-cost baseline, 252/365 annualisation, sentiment lag, and the rule
> that Part A full-sample statistics must not influence Part B weights."

### What the assistant produced

The assistant preserved the supplied data loader and ported my completed Part A
modules for ETL, calendar alignment, features, plotting and innovation. Running
them against the official data reproduced 50,300 clean equity rows, 14,610
clean crypto rows after dropping ten observations dated 2024-01-01, 146,830
deduplicated headlines and a 37,962-row ticker-day headline panel. It recorded
the fixed assumptions in `report/OUTLINE.md` and repeated the no-look-ahead
rules in the project instruction files.

The only structural difference was physical location. The brief illustrates a
folder under `fins-agent/fins2026/`, while my standalone repository is at
`D:\新南威尔士 UNSW\T2\FINS5545\FINS 5545 CODEX\z5652591_projectB`.
All project code uses paths relative to the repository root, so the different
parent folder does not change the calculations, Git remote or deployment.

### What was wrong or risky

The main risk was confusing permission to reuse my Part A code with permission
to reuse Part A full-sample results. If a historical Part B rebalance used a
mean, covariance or sentiment baseline calculated over all of 2020-2023, it
would contain information dated after that decision. The program could still
run and produce plausible Sharpe ratios, so this look-ahead would not
necessarily appear as a software exception. Two possible exposure caps also
remained unresolved; allowing an AI-suggested default to enter the baseline
would defeat the purpose of freezing assumptions before results existed.

### What I changed and why

I checked the row counts against my own Part A evidence rather than relying
only on the assistant's summary. I kept `src/data_access.py` frozen and wrote
the no-look-ahead restriction into `AGENTS.md`, `CLAUDE.md` and
`report/OUTLINE.md`, with mechanical timing tests required later. I deliberately
left the proposed caps unresolved until comparing the specification with the
course reference in the next stage.

---

## 2. Check the backtest specification against the course reference (13 August 2026)

### What I wanted

Before writing the backtest, compare my planned specification with the Week 10
worked example. I wanted differences in scope, formulas and constraints made
explicit before performance results made it tempting to choose a more
attractive specification.

### Prompt(s)

> "Read the Week 10 worked example and compare my planned specification line by
> line: universes, methods, formulas, constraints, timing and reporting. Tell
> me exactly where they differ."

> "Where the plans disagree, explain both alternatives and what difference
> each choice could make to the results. Do not choose silently for me."

### What the assistant produced

The comparison identified two material differences. My original plan contained
three methods, while the course example used four methods across three asset
universes, giving 12 funds. My outline also proposed arbitrary 20% single-asset
and 30% crypto caps, whereas the reference used long-only, fully-invested
portfolios without those caps and treated concentration as a result to analyse.
The assistant also extracted the reference fusion rule: multiply each base
equity weight by `1 + lambda * sector_z_score`, clip negative adjusted weights
to zero and renormalise.

### What was wrong or risky

A capped, three-method implementation could be internally consistent and still
be too narrow relative to the demonstrated baseline. It would omit Maximum
Sharpe and mechanically suppress concentration that should instead be visible
and interpreted. This was a scope and research-design risk rather than a syntax
error. Changing methods or constraints after seeing performance would create a
second risk: choosing the specification because it improved the backtest.

### What I changed and why

I changed the frozen baseline to three universes by four methods: equal weight,
minimum variance, maximum Sharpe and risk parity. I removed the arbitrary caps
and retained long-only, fully-invested constraints. A capped version could only
be added later as a clearly labelled sensitivity check, not as a replacement
for the baseline. I also adopted the explicit sector-level fusion equation and
required its window and lambda values to be fixed before viewing its results.

---

## 3. Implement the 12-fund walk-forward backtest engine (13 August 2026)

### What I wanted

Implement a clean expanding-window backtest: monthly decisions, weights
effective on the next available trading day, different equity and crypto
calendar conventions, holdings that drift with returns between rebalances, and
an audit trail plus adversarial tests that catch timing and constraint errors.

### Prompt(s)

> "Implement equal weight, minimum variance, maximum Sharpe and risk parity for
> the equity, crypto and combined universes. Every portfolio must be long-only
> and fully invested."

> "The estimation window ends on the rebalance decision date and the new
> weights become effective on the next available trading day. Keep
> `estimation_end`, `rebalance_date` and `effective_date` separate. Never use
> same-effective-day information."

> "Use a 252-trading-day initial window for equity and combined funds and 365
> calendar days for crypto. Annualise equity and combined with 252 and crypto
> with 365."

> "Write tests for strict date ordering, weights summing to one, no negative
> weights, 36 monthly decisions per fund, and different weight matrices across
> methods. Make optimiser failure explicit rather than returning a silent
> fallback."

### What the assistant produced

The assistant implemented the four methods and shared OOS engine in
`src/portfolios.py`, together with performance metrics, long-format weights and
a rebalance audit. The final real-data build contains all 12 funds and 36
monthly decisions per fund. The first live dates are 5 January 2021 for equity
and combined funds and 2 January 2021 for crypto. Tests use an absolute
tolerance of `1e-8` for full investment and `-1e-12` as the numerical lower
bound for non-negative weights; all estimation periods end before the related
effective dates.

### What was wrong or risky

Two silent problems appeared during implementation. First, the original
risk-parity starting scale was inconsistent with the log-barrier risk-budgeting
objective and caused an L-BFGS-B line-search failure. A plausible weight vector
would not by itself prove that the intended optimisation had succeeded. Second,
the first schedule grouped only the eligible tail of the calendar. It treated
31 December 2020 as an extra monthly decision and produced 37 rebalances rather
than the expected 36. Both problems could have generated reasonable-looking
tables without a dedicated audit.

### What I changed and why

I inspected the risk-parity objective and changed its starting scale to
`sqrt(risk_budget / asset_variance)`, while requiring the optimiser to fail
loudly if it did not converge. I changed the calendar logic to identify each
month's decision date from the complete calendar before applying estimation-
window eligibility. I manually checked the 36 expected months and reran the
real-data audit. Every fund then passed date ordering, non-negativity and
full-investment checks, and each pair of methods within a family produced
materially different allocations.

---

## 4. Build sentiment models and complete human validation (13-14 August 2026)

### What I wanted

Build two comparable sentiment models - plain VADER as the baseline and a
finance-enhanced lexicon as the treatment - through one shared pipeline. I
wanted sector-level daily indices, a strict one-trading-day lag and blank review
materials so that I, rather than the AI, judged the model and proposed terms.

### Prompt(s)

> "Score each headline individually, preserve its original casing and
> punctuation, aggregate ticker-day scores to an equal-weight sector index, and
> keep no-news days different from neutral-news days."

> "Build plain and finance-enhanced VADER through the same pipeline so only the
> reviewed finance lexicon changes."

> "Map news to the equity trading calendar and apply a one-trading-day lag. A
> weekend headline first mapped to Monday may influence Tuesday, never Monday."

> "Prepare 24 candidate finance terms with proposed scores and explanations,
> all marked `student review required`. Prepare exactly 50 blank headline
> review rows, five per sector. Do not fill in any student decision."

### What the assistant produced

The assistant implemented per-headline scoring, ticker-day aggregation,
equal-weight sector aggregation, explicit no-news rows and a plain-versus-
enhanced comparison. It proposed 24 finance terms and generated a stratified
50-headline review file with all student fields blank. On the 146,830
deduplicated headlines, the enhanced lexicon reduced the neutral classification
rate from 49.573657% to 47.809031%, a modest decline of 1.7646 percentage points.
Both models use the same classification thresholds and processing steps.

### What was wrong or risky

An early comparison assumed rows remained unique after mapping news to trading
days. They do not: distinct weekend or holiday headlines can map to the same
trading date and may share a mapped key. Deduplicating again after mapping would
discard valid observations. Calendar alignment also is not the same as a
trading lag; using weekend news in Monday's effective weight would still leak
same-effective-day information. Finally, AI-proposed labels and lexicon
rationales could not honestly be presented as human validation.

### What I changed and why

I retained the Part A exact-duplicate rule on `(ticker, original date, title)`
but did not deduplicate distinct headlines again after mapping. I required a
stable `headline_id`, separated the mapped observation date from the first
usable signal date, and traced weekend examples through the calendar. I then
personally labelled all 50 sampled headlines and reviewed all 24 finance terms,
accepting the terms only after reading their score and rationale. The completed
validation reports 66% agreement for plain VADER and 70% for enhanced VADER;
positive agreement rises from 66.7% to 80.0%, while negative agreement remains
33.3%. I kept this mixed evidence rather than claiming that the enhanced model
was generally accurate.

---

## 5. Add lag-safe sentiment fusion without tuning to OOS results (13 August 2026)

### What I wanted

Test whether lagged sector sentiment changes the equity minimum-variance fund
under a non-negotiable research rule: all parameters and signal directions had
to be fixed before viewing outcomes. I wanted no tilt, momentum and contrarian
variants reported together, with no post-hoc search for a winning sign.

### Prompt(s)

> "Apply the sector sentiment tilt to the equity minimum-variance portfolio.
> Every stock inherits its sector's lagged z-score. Use `weight * (1 + lambda *
> z_score)`, clip negative adjusted weights and renormalise."

> "Fix lambda at 0, +1 and -1. Use a fixed 60-trading-day z-score window with
> 20 minimum observations. Do not search for better values and do not remove an
> underperforming result."

> "If a sentiment observation is unavailable, use zero tilt but keep an
> availability flag. Verify that lambda zero exactly reproduces the base
> portfolio."

### What the assistant produced

The assistant produced base (`lambda=0`), momentum (`lambda=+1`) and contrarian
(`lambda=-1`) variants, with `sentiment_source_date` required to precede
`effective_date`. Missing sentiment produces zero tilt and remains flagged.
The lambda-zero variant reproduced the base minimum-variance weights exactly,
and every variant remained long-only and fully invested. In the final corrected
OOS results, Sharpe ratios are 0.591 for base, 0.630 for momentum and 0.741 for
contrarian.

### What was wrong or risky

The main risk was research integrity rather than a software exception. Searching
window lengths or signs on the OOS period and retaining only the best result
would turn noise mining into an apparently successful strategy. The lambda-zero
invariant was also necessary: if renormalisation changed the zero case, the
differences could not be attributed to sentiment. A wording risk also appeared
when the implementation was described as a ticker-level signal even though all
stocks in one sector receive the same sector score.

### What I changed and why

I froze the 60/20 window and all three lambda values, kept every variant side by
side and changed the project wording to `sector-level tilt`. Contrarian's higher
Sharpe ratio is reported as one of three pre-specified outcomes, not as proof
that I selected the correct sign or that the result will persist. The exact
lambda-zero identity and lag conditions remain automated tests.

---

## 6. Add covariance shrinkage and transaction-cost robustness checks (14 August 2026)

### What I wanted

Add two evidenced extensions beyond the course baseline: Ledoit-Wolf covariance
shrinkage and transaction-cost sensitivity. Both had to remain labelled
comparisons rather than silently replacing the baseline, and turnover had to be
calculated from holdings that actually drift between rebalances.

### Prompt(s)

> "Run Ledoit-Wolf covariance shrinkage alongside sample covariance. Do not
> replace the baseline estimator; use the same expanding windows and OOS dates
> and report both."

> "Calculate one-way transaction costs at 0, 10, 25, 50 and 100 basis points.
> Compound holdings between rebalances and measure turnover from drifted
> pre-trade weights to the new targets."

> "Do not change a model parameter to improve a result. If correcting holdings
> mechanics changes earlier numbers, document and regenerate them instead of
> preserving an obsolete hash."

### What the assistant produced

The assistant added `src/robustness.py`, shrinkage comparison tables,
transaction-cost curves, Figures A7-A8 and a sixth Streamlit page. Sample
covariance remains the baseline and Ledoit-Wolf is an explicit alternative.
The portfolio engine records target weight, drifted pre-trade weight, trade
change and one-way turnover at each effective rebalance. The same drift logic is
used in baseline, robustness and sentiment-fusion returns.

### What was wrong or risky

An earlier return engine effectively restored target weights every day, and
turnover was derived from consecutive target vectors. In reality, relative
asset returns cause weights to drift; the next trade is from the drifted
pre-trade portfolio to the new target. Ignoring this understates turnover and
transaction costs, most visibly for equal weight, where the incorrect approach
can imply zero trading. Preserving the earlier baseline files after finding this
error would have made the reproducibility claim reproduce the wrong mechanics.

### What I changed and why

I required daily holdings drift and defined one-way turnover as
`0.5 * sum(abs(target_weight - pre_trade_weight))`, with initial funding assigned
zero turnover. I added deterministic tests for the drift and turnover algebra
and confirmed non-zero equal-weight turnover. This implementation correction
changed return, weight, fusion, shrinkage and cost files, but it did not change
an optimisation method or tuned parameter. I regenerated all affected results
and explained the finding that even simple target allocations incur trading
costs.

---

## 7. Build the final report and investor-facing application (14 August 2026)

### What I wanted

Turn the model evidence into a coherent product: a report satisfying every
required exhibit and interpretation requirement, and a light Streamlit app
supporting fund comparison, fact sheets, allocation choice and sentiment
analytics. I wanted my own financial-language revisions and a professional UNSW
cover preserved.

### Prompt(s)

> "Check the complete report against the Part B rubric. Make every table and
> Figure A1-A8 self-contained, cited in the narrative and interpreted, and add
> the required before-versus-after sentiment-fusion evidence."

> "Keep my manual financial interpretation, use Harvard author-date citations,
> and adapt the uploaded UNSW report cover only as a visual reference while
> retaining the correct FINS5545 individual-project details."

> "Build a polished Streamlit investor journey that reads only precomputed
> `results/` files: Home, Fund Comparison, Fund Fact Sheet, Allocation Builder,
> Sentiment Analytics and Robustness Lab. Do not run NLTK or backtests in the
> deployed app."

### What the assistant produced

The assistant audited the report against the brief, added the missing fusion
comparison table, cross-referenced and interpreted all Figures A1-A8, corrected
terms such as expanding window, sector-level tilt and covariance shrinkage, and
repaired the Harvard references. It adapted the cover hierarchy from the
uploaded example while retaining the correct course, zID and individual
submission details. The final report has 2,654 narrative words across seven
narrative pages and 14 pages including cover, appendices and references.

The app exposes all six planned pages and reads only committed precomputed
artifacts. It presents 12 funds, three asset families, four methods, current
holdings, allocation outputs, sector sentiment, fusion results, shrinkage and
transaction-cost sensitivity, with risk disclosures for an investor audience.

### What was wrong or risky

The cover reference came from a different course and group submission, so
copying its wording would introduce false information. During an early automated
Word edit, a generic replacement loop assigned empty text to picture and page-
break runs; the document opened but lost figures and its cover break. Separate
even-page footer settings also pushed some page numbers partly outside the page.
Content-wise, not every appendix figure was initially referenced in the main
narrative, and the fusion figure existed without the required report table.

### What I changed and why

I used the uploaded PDF only for visual hierarchy and retained the correct
authorship and course details. I restored the Word file from the pre-edit copy,
restricted edits to text runs that actually changed, preserved picture/page-
break XML and disabled inconsistent even-page headers and footers. I rendered
all 14 pages and checked figures, captions, tables, clipping and pagination
before replacing the final PDF. I also protected my final edited Word source by
changing `scripts/build_report.py` to create the ignored
`report/report_generated_draft.docx` instead of overwriting `report/report.docx`.

---

## 8. Reproduce, test, deploy and prepare the final hand-in (14 August 2026)

### What I wanted

Prove that the final project reproduces from a clean state, verify every tracked
result rather than a selected subset, run all timing and submission checks,
remove stale artifacts, publish the correct repository, verify the public app
and prepare a clean Moodle archive.

### Prompt(s)

> "Compare every tracked file under `results/` with what a clean
> `python scripts/run_part_b.py` run produces. Remove or explain every orphaned
> file; do not call the project reproducible after checking only four files."

> "Run the complete tests, `tests/test_no_lookahead.py --real` and
> `scripts/check_handin.py`. Report failures and warnings without changing
> methods or parameters to force a pass. Check that no raw data, credentials,
> caches or secrets are committed."

> "Confirm the exact GitHub repository, visibility and branch, push the final
> project, test Streamlit locally, and prepare a ZIP from the verified Git
> snapshot. Do not claim a live deployment until the public URL works."

> "Verify my deployed app at
> https://z5652591projectb-carymh8kgzkfbrbzdhyjr7.streamlit.app/ and check every
> page rather than only the home page."

> "For the final Moodle package, retain the teacher-provided structure, full
> code, reproducible results, report and AI workflow, but remove redundant
> internal documents. Do not delete evidence required by the app or rebuild."

### What the assistant produced

A broad audit found three stale split fusion files that the current pipeline no
longer produced, so they were removed. After the holdings and human-review
corrections, a clean `scripts/run_part_b.py` run recreated exactly 28 result
files: seven data CSVs, nine figures and 12 tables. It produced 10,392 fund-
return rows, 17,280 weight rows, 20,120 sector-index rows, 12 fund metrics and
all completed manual-review evidence. No committed result is absent from a
fresh build.

The final test suite passed 13 tests. The separate real-data audit passed all 12
funds and 36 rebalances per fund, and `scripts/check_handin.py` passed 23 checks
with zero warnings after cache cleanup. `src/data_access.py` remained untouched.
The public repository is
`https://github.com/RUOYUNWU-ui/z5652591_projectB` on `main`. The live app was
opened without an authenticated Streamlit session and all six pages displayed
their expected content without application alerts. A final Git-snapshot ZIP was
created for Moodle. The final packaging audit removed three superseded internal
documents whose evidence had already been consolidated into this log and the
submission outputs; the resulting tracked submission contains 70 files.

### What was wrong or risky

Earlier checks compared only four required files and at one stage described a
21-file output set. That could leave stale committed evidence outside the audit.
The first clean rebuild also exposed an environment problem: Anaconda's
`pyarrow 19` raised `Repetition level histogram size mismatch` on the official
Parquet data. Editing the frozen loader or keeping old results instead of
rebuilding would have weakened reproducibility. Local Streamlit HTTP success was
also not proof that a public deployment worked, and a public GitHub repository
was not a substitute for the required live URL.

### What I changed and why

I expanded reproducibility from selected hashes to the complete 28-file
manifest and removed outputs a clean build no longer creates. I did not modify
the loader; I ran the official pipeline in the existing project environment
with `pyarrow 24` and the backup URL already supported by the frozen loader.
After testing, I removed generated caches, reran the hand-in checker, committed
and pushed the verified snapshot, and rebuilt the ZIP from Git rather than from
an unfiltered working folder. For the last packaging pass, I kept every starter
file, runtime dependency, test, report source, AI record and reproducible result,
but removed the duplicate completion matrix, superseded manual-review
instructions and internal QA report after consolidating their relevant evidence.
I accepted deployment as complete only after an independent page-by-page public-
browser check. Moodle upload remains my own authenticated submission action.

---

## Verification and reproducibility summary

| Stage | AI-assisted risk or error | How I identified it | Verification or correction |
|---|---|---|---|
| Data foundation | Part A source could drift or full-sample evidence could enter OOS decisions | Compared the official brief, source roles and published Part A counts | Manual count check: 50,300 equity, 14,610 crypto, 146,830 deduplicated headlines; frozen loader unchanged |
| Backtest scope | Three methods and arbitrary caps were narrower than the course reference | Performed a line-by-line specification comparison before coding | Froze 3 universes x 4 methods, long-only and fully invested |
| Risk parity | Solver starting scale did not match the objective | Inspected the objective and treated convergence failure as an error | Corrected starting scale and required explicit solver success |
| Rebalance calendar | Eligible-tail grouping created 37 rather than 36 decisions | Counted calendar months and reviewed the schedule construction | Built dates from the full calendar; real-data audit confirms 36 decisions per fund |
| Sentiment mapping | Post-mapping deduplication could discard valid weekend/multi-source headlines | Traced distinct headlines through the trading-day mapping | Deduplicate only original `(ticker, date, title)` rows; retain stable headline IDs |
| Sentiment lag | A weekend headline could affect Monday rather than Tuesday | Manually traced observation, mapped and usable dates | Require sentiment source date to precede effective date |
| Human validation | AI could appear to validate its own labels and lexicon | Kept student fields blank until personal review | Completed 50 headline labels and reviewed all 24 finance terms |
| Fusion | Parameter search or renormalisation could bias the result | Froze the 60/20 window and lambda values and required a zero-case invariant | Automated lambda-zero equality; all three variants retained |
| Portfolio mechanics | Daily reset to targets understated turnover and costs | Reasoned from drifted holdings and tested a deterministic example | Pre-trade-to-target turnover, non-zero equal-weight turnover and regenerated results |
| Reproducibility | Four-file/21-file checks could miss orphaned outputs | Compared Git-tracked results with a genuinely clean build | Exact 28-file manifest; 13 tests, real-data audit and 23 hand-in checks pass |
| Report | Automated Word edits could silently remove non-text objects | Rendered every DOCX page instead of trusting that it opened | Restored figures and breaks; checked all 14 pages visually |
| Deployment | Local success or a URL alone did not prove public usability | Opened the public URL without the deployment account and navigated every page | Six live pages verified without application alerts |

## Limitations of this AI-assisted workflow

Mechanical checks are strong at detecting date-ordering, constraint, schema,
drift and reproducibility failures, but they cannot decide whether an economic
interpretation is reasonable. A passing test proves only the condition encoded
by that test. I therefore combined automated checks with manual traces of the
calendar, manual review of optimiser assumptions, visual inspection of the
report, and human sentiment labels. The enhanced VADER validation is mixed,
crypto Sharpe ratios remain below the Week 10 reference despite matching the
audited crypto return moments, and contrarian fusion's stronger OOS result does
not establish future predictability. These limitations remain in the report
rather than being tuned away.

## Final note on my responsibility

I personally rewrote the report's economic analysis and interpretation in my
own words. I labelled all 50 sampled headlines and reviewed all 24 proposed
finance lexicon entries one by one before accepting them. I reviewed the course
requirements and the corrections described above rather than treating an AI
response, a successful script run or an attractive Sharpe ratio as sufficient
evidence. I also completed the Streamlit deployment through my own account. The
public repository and live application are:

- `https://github.com/RUOYUNWU-ui/z5652591_projectB`
- `https://z5652591projectb-carymh8kgzkfbrbzdhyjr7.streamlit.app/`

All reported findings are retained, including mixed sentiment validation,
weaker crypto performance and implementation costs, because transparency is
more important than presenting only favourable outcomes.
