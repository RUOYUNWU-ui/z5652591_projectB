# Prompt log - FINS5545 Project B (z5652591)

This log follows the five-field structure in the provided
`ai/prompt_log_template.md`. It records what I asked an AI assistant to do,
what it produced, the risks or errors I identified, and the changes I made
after checking the output against the course material, source code, tests and
generated evidence. The prompts are grouped by task so the record remains
readable; they are not presented as work completed without human review.

## 1. Project setup - reuse Part A and freeze assumptions before coding (13 August 2026)

### What I wanted

Build Part B on my completed Part A foundation, reusing only the modules
permitted by the brief. Before portfolio or sentiment code was written, I
wanted the estimation windows, rebalance schedule, constraints, annualisation
rules and sentiment lag recorded so they could not be adjusted after seeing
results.

### Prompt(s)

> "Port the Part A data loading, cleaning, calendar-merging and feature modules
> unchanged into this Part B project, but do not overwrite the starter
> `src/data_access.py`."

> "Read the official project brief and project structure documents. Compare my
> plan against them line by line and flag mismatches in filenames, folder
> layout, fund matrix, rules and deliverables."

> "Write the frozen assumptions in the outline: universes, methods, initial
> windows, rebalance frequency, weight timing, long-only constraints,
> risk-free rate, baseline transaction costs, annualisation days, sentiment
> lag, and the rule that Part A full-sample statistics must not influence Part
> B weights."

### What the assistant produced

The assistant confirmed that the starter `src/data_access.py` was byte-for-byte
identical to the supplied loader used in Part A and left it untouched. It
ported my completed Part A `etl.py`, `calendar_merge.py`, `features.py`,
`plot_style.py` and `innovation.py`, then ran the pipeline against the official
data. The checks reproduced 50,300 clean equity rows, 14,610 clean crypto rows
after removing the ten 2024 observations, 146,830 deduplicated headlines and a
37,962-row ticker-day headline panel. It also added the frozen assumptions to
`report/OUTLINE.md` and documented the no-look-ahead restriction.

The assistant identified one non-code layout difference: the brief illustrates
`fins-agent/fins2026/z5652591_projectB`, whereas my repository is located at
`D:\新南威尔士 UNSW\T2\FINS5545\FINS 5545 CODEX\z5652591_projectB`.
The code uses project-relative paths, so this location difference does not
change the calculations.

### What was wrong or risky

The main risk was confusing permission to reuse my Part A code with permission
to reuse Part A full-sample results. If a Part B rebalance used a mean,
covariance or sentiment baseline calculated over all of 2020-2023, that
statistic would include information dated after the historical decision. The
code could still run and produce plausible Sharpe ratios, so this form of
look-ahead would not necessarily reveal itself as a software error. Two
proposed exposure caps were also still unresolved at this stage; silently
accepting an AI-suggested default would have violated the purpose of freezing
the design before observing performance.

### What I changed and why

I checked the reproduced row counts against my submitted Part A evidence rather
than relying only on the assistant's summary. I kept the starter data loader,
recorded the full-sample restriction in `CLAUDE.md`, `AGENTS.md` and
`report/OUTLINE.md`, and required the later no-look-ahead tests to enforce it.
I left the proposed caps unresolved until I compared the specification with
the course reference in the next task instead of allowing them to become
implicit defaults.

---

## 2. Check the backtest specification against the course reference (13 August 2026)

### What I wanted

Before implementation, compare my planned portfolio specification with the
Week 10 worked example so that differences in scope, formulas and constraints
were resolved before results existed.

### Prompt(s)

> "Read the worked example in the course revision lecture. Compare my planned
> specification line by line: universes, methods, formulas, constraints,
> timing and reporting. Tell me exactly where they differ."

> "Where the plans disagree, explain both alternatives and the likely effect
> on the results. Do not choose silently on my behalf."

### What the assistant produced

The comparison identified two material differences. My original outline had
three methods, while the reference used four methods across three universes,
giving 12 funds. My outline also proposed 20% single-asset and 30% crypto caps
without empirical or course support, whereas the reference used long-only,
fully invested portfolios without those caps and treated concentration as an
economic result to interpret. The assistant also extracted the reference
fusion rule: multiply base weights by `1 + lambda * z_score`, clip at zero and
renormalise.

### What was wrong or risky

A three-method capped implementation would not necessarily contain a coding
error, but it would be narrower than the baseline demonstrated by the course
and would suppress the concentration pattern that the reference treats as a
finding. This was therefore a scope and research-design problem rather than a
syntax problem. Once performance results existed, changing the methods or caps
would also create a risk of selecting a specification because it produced a
more attractive backtest.

### What I changed and why

I changed the frozen baseline to three universes by four methods: equal weight,
minimum variance, maximum Sharpe and risk parity. I removed the arbitrary caps
and retained long-only, fully invested constraints. Any future capped version
would have to be labelled as a separate sensitivity check rather than replacing
the baseline. I also replaced the vague fusion description with the course
formula and recorded that its window and lambda values had to be chosen before
viewing the fusion results.

---

## 3. Implement the 12-fund walk-forward backtest (13 August 2026)

### What I wanted

Implement expanding-window, monthly rebalanced equity, crypto and combined
funds with weights effective on the next trading day, plus an audit trail and
tests that mechanically detect timing and constraint failures.

### Prompt(s)

> "Implement equal weight, minimum variance, maximum Sharpe and risk parity.
> Every portfolio must be long-only and fully invested."

> "Estimation ends on the rebalance decision date and weights become effective
> on the next available trading day. Keep `estimation_end`, `rebalance_date`
> and `effective_date` separate so the timing can be audited."

> "Use at least 252 observations for equity and combined funds and 365 calendar
> observations for crypto. Annualise equity/combined with 252 and crypto with
> 365."

> "Add tests for strict date ordering, weights summing to one, non-negative
> weights, the expected number of monthly decisions and different allocations
> across the four methods."

### What the assistant produced

The assistant implemented the four methods in `src/portfolios.py`, a shared OOS
backtest, performance metrics, long-format weights and a rebalance audit. The
real-data run produced all 12 funds with 36 monthly decisions per fund. The
first live dates were 5 January 2021 for equity and combined funds and 2 January
2021 for crypto. Tests used an absolute tolerance of `1e-8` for full investment
and `-1e-12` as the numerical lower bound for non-negative weights; estimation
always ended before the effective date.

### What was wrong or risky

Two silent implementation errors appeared during testing. First, the initial
risk-parity solver scale was normalised incorrectly before the log-barrier
risk-budgeting optimisation, causing an L-BFGS-B line-search failure. A solver
returning a plausible vector is not enough evidence that it solved the intended
economic problem. Second, the first schedule grouped only the eligible tail of
the calendar. This treated 31 December 2020 as December's first eligible date
and produced 37 decisions instead of the expected 36. Both errors could have
produced reasonable-looking output without an explicit audit.

### What I changed and why

I checked the risk-parity objective and changed its starting scale to
`sqrt(risk_budget / asset_variance)`, then required the optimiser to fail loudly
if it did not converge. I changed the schedule logic to find each month's first
date from the complete calendar and only then apply estimation-window
eligibility. I manually checked the expected 36 months and reran the real-data
test. All 12 funds then had 36 rebalances, weight sums were within machine
precision, all weights were non-negative, every estimation end preceded its
effective date, and every pair of methods within an asset family had different
weight matrices.

---

## 4. Build plain and finance-enhanced VADER sentiment models (13-14 August 2026)

### What I wanted

Build comparable plain and finance-enhanced VADER models using one scoring
pipeline, create a sector-level daily sentiment index with a strict trading-day
lag, and prepare genuinely blank human-review material rather than allowing the
AI to validate its own labels.

### Prompt(s)

> "Score every headline individually and aggregate ticker-day scores to a daily
> sector index. Preserve original title casing and punctuation."

> "Build plain and finance-enhanced VADER through the same pipeline so only the
> reviewed finance lexicon changes."

> "Map headlines to the trading calendar and require at least a one-trading-day
> lag before sentiment can influence weights. Keep no-news days different from
> neutral-news days."

> "Prepare 24 candidate finance terms marked `student review required` and
> exactly 50 blank headline-review rows, five per sector. Do not fill in the
> student decisions."

### What the assistant produced

The assistant implemented per-headline scoring, ticker-day aggregation,
equal-weight sector aggregation, explicit no-news rows and plain-versus-enhanced
comparison. It created a 24-term candidate lexicon and a stratified 50-headline
review file with the student fields blank. On 146,830 deduplicated headlines,
the enhanced lexicon reduced the neutral classification rate from 49.573657%
to 47.809031%, a decrease of 1.7646 percentage points. The same pipeline and
thresholds were used for both models.

### What was wrong or risky

An early comparison assumed that mapped `(date, ticker, sector, title)` rows
were unique. They are not: distinct headlines published on weekends or
holidays can map to the same trading day and may share the mapped key. Removing
them after calendar mapping would discard valid observations. There was also a
timing risk: rolling a weekend headline to Monday is only date alignment, not
the trading lag. Using that value for Monday's position would still use
same-effective-day information. Finally, AI-generated lexicon explanations and
model labels could not be presented as human validation.

### What I changed and why

I retained the Part A exact-duplicate rule `(ticker, original date, title)` but
did not deduplicate distinct rows again after trading-day mapping. Each retained
headline received a stable `headline_id` for aligning plain and enhanced scores.
The mapped observation date and usable signal date were separated: weekend news
first maps to Monday and can influence Tuesday's effective position, not
Monday's. I then personally completed all 50 headline judgements and reviewed
all 24 finance terms. Those human-only fields are preserved in
`report/sentiment_manual_review_annotations.json` and restored after a clean
build. The completed validation reports 66% agreement for plain VADER and 70%
for enhanced VADER; positive agreement rises from 66.7% to 80.0%, while
negative agreement remains 33.3%. I kept this mixed result instead of claiming
that the enhanced model was generally accurate.

---

## 5. Add lag-safe sentiment fusion without tuning to OOS results (13 August 2026)

### What I wanted

Test a sector-level sentiment tilt on the equity minimum-variance fund while
fixing all signal parameters and directions before viewing results. The zero
tilt had to reproduce the base fund exactly.

### Prompt(s)

> "Apply the sentiment tilt to the equity minimum-variance portfolio. Every
> stock inherits its sector's lagged z-score. Use `weight * (1 + lambda *
> z_score)`, clip negative values and renormalise."

> "Fix lambda at 0, +1 and -1. Do not search for better values and do not remove
> an underperforming variant."

> "Fix the rolling z-score window before viewing results. If sentiment is
> unavailable, use zero tilt and retain an availability flag."

> "Verify that lambda zero reproduces the base weights exactly. If it does not,
> treat that as an implementation error."

### What the assistant produced

The assistant implemented base (`lambda=0`), momentum (`lambda=+1`) and
contrarian (`lambda=-1`) variants using a 60-trading-day standardisation window
with 20 minimum observations. Missing signals produce zero tilt and remain
flagged as unavailable. The implementation records `sentiment_source_date` and
requires it to be earlier than `effective_date`. The lambda-zero case passed
exact row equality with the base minimum-variance weights, and every tilted
portfolio remained long-only and fully invested.

### What was wrong or risky

The main risk was research integrity rather than a software exception. Searching
over window lengths or signs during the OOS period and retaining only the winner
would convert noise mining into an apparently successful strategy. The
lambda-zero invariant was also essential: if renormalisation changed the zero
case, performance differences could not be attributed to sentiment. A further
wording risk was calling the implementation ticker-level; the signal is
sector-level because all stocks in a sector receive the same lagged z-score.

### What I changed and why

I froze the 60/20 window and all three lambda values without a parameter search,
kept all three results side by side, and updated the outline, report and app to
describe a sector-level tilt. The final drift-corrected OOS results are reported
without changing the specification: Sharpe ratios are 0.591 for the base,
0.630 for momentum and 0.741 for contrarian. Contrarian performing best is
described as one pre-specified outcome, not as proof that the sign was selected
correctly or will persist.

---

## 6. Add covariance shrinkage and transaction-cost robustness checks (14 August 2026)

### What I wanted

Add Ledoit-Wolf covariance shrinkage and transaction-cost sensitivity as
labelled extensions, while calculating monthly turnover from the holdings that
actually drift between rebalances rather than from successive target vectors.

### Prompt(s)

> "Run Ledoit-Wolf covariance shrinkage alongside sample covariance; do not
> silently replace the baseline estimator. Use the same expanding windows and
> OOS dates."

> "Apply one-way costs of 0, 10, 25, 50 and 100 basis points. Calculate turnover
> from drifted pre-trade weights to the new monthly target."

> "Keep the method choices and parameters fixed. If correcting portfolio drift
> changes previously generated numbers, document the change rather than trying
> to preserve an obsolete result."

### What the assistant produced

The assistant added a separate robustness module, shrinkage comparison table,
transaction-cost curves, two figures and a sixth Streamlit page. Sample
covariance remains the baseline and Ledoit-Wolf is an explicitly selected
extension. It also added daily holdings drift and records pre-trade weight,
target weight, trade change and one-way turnover at every effective rebalance.
The same holdings mechanics are used for the base, robustness and fusion
portfolios.

### What was wrong or risky

The earlier return engine effectively returned to target weights every day,
and turnover was derived from consecutive targets. In reality, relative asset
returns move the holdings away from target between monthly rebalances. Measuring
the next trade from the previous target understates turnover and transaction
costs, most visibly for equal weight, where an incorrect implementation can
suggest zero turnover. Preserving the earlier hashes after finding this error
would have been misleading because those hashes represented the wrong
implementation.

### What I changed and why

I required holdings to drift with realised returns and calculated turnover as
`0.5 * sum(abs(target_weight - pre_trade_weight))`; initial funding is assigned
zero turnover. I added tests that reproduce the drift and turnover algebra on a
small deterministic example and confirm non-zero equal-weight turnover. This
implementation correction changed baseline returns, weights, fusion results,
shrinkage comparisons and cost curves, but it did not change a model parameter
or optimisation method. The report therefore uses only the regenerated,
drift-corrected results and explains that even simple target allocations incur
implementation costs.

---

## 7. Reproducibility, testing and submission checks (14 August 2026)

### What I wanted

Establish that the final outputs are recreated by the single official script,
remove stale committed results, run the real-data timing audit and official
hand-in checker, and distinguish a public repository from a verified live app.

### Prompt(s)

> "Compare every tracked file under `results/` with the manifest produced by a
> clean `python scripts/run_part_b.py` run. Remove orphaned results that a clean
> build does not reproduce."

> "Run the full tests, the real-data no-look-ahead audit and
> `scripts/check_handin.py`. Report failures and warnings rather than silently
> changing parameters or results."

> "Check that no raw data, credentials or unnecessary cache files are committed.
> Confirm the exact repository owner/name, visibility and default branch."

### What the assistant produced

The first broad comparison found stale files from an earlier pipeline version
and removed those orphaned generated artifacts from version control. After the
human-review preservation and holdings-drift corrections, a clean
`scripts/run_part_b.py` build produced exactly 28 files: seven data CSVs, nine
figures and 12 tables. No tracked result was absent from the clean manifest.
The final test suite passed 13 tests, and the separate real-data audit passed
all 12 funds and 36 decisions per fund. At the recorded clean-hand-in checkpoint,
`scripts/check_handin.py` passed 23 checks with no warnings after generated
Python caches were removed. The frozen `src/data_access.py` remained unchanged.

The assistant also confirmed the public repository as
`RUOYUNWU-ui/z5652591_projectB`, with default branch `main`. It did not find a
verified live Streamlit URL in the repository.

### What was wrong or risky

Earlier reproducibility wording referred only to four required files and, at an
intermediate stage, a 21-file manifest. That was too narrow and later became
outdated as the robustness and completed human-review outputs were added. A
stale generated file could remain committed even though the four selected
hashes matched. Another risk was treating a public GitHub repository as proof
of deployment; the brief requires both the public repository and a working
live Streamlit URL. Finally, `__pycache__` and `.pyc` files can reappear after
tests even when the underlying submission is otherwise correct.

### What I changed and why

I expanded the comparison from selected outputs to the full final manifest and
kept the reproducible entry point as `scripts/run_part_b.py`. I retained the
final required-file SHA-256 values and complete audit details in
`report/QA_REPORT.md`, rather than copying changing hashes into the narrative
report. I authorised making the repository public and verified its current
identity. I did not claim that Streamlit was deployed because the live URL was
not verified; confirming that URL remains a student submission action. I also
accepted the hand-in checker's cache warning as a packaging reminder rather
than changing any model result.

The checks catch date ordering, constraints, drift algebra and reproducible
files, but they cannot determine whether an economic interpretation is
reasonable. I therefore rewrote the report's financial discussion in my own
words, completed the 50 headline labels myself and reviewed all 24 lexicon
entries. Mixed and weaker results remain reported instead of being tuned away.

---

## 8. Audit the final report and adapt the supplied UNSW cover (14 August 2026)

### What I wanted

Check the complete report against the Part B rubric and use the uploaded UNSW
report as a visual cover reference, while keeping the correct FINS5545,
individual-project and student details.

### Prompt(s)

> "Check whether the full report meets the teacher's requirements and change
> the cover to the format of the PDF I uploaded."

> "Keep my manual financial-language revisions, use Harvard in-text citations,
> and correct only content or formatting that conflicts with the brief or the
> implemented program."

### What the assistant produced

The assistant compared the report with `PROJECT_BRIEF.md`, inspected the
reference PDF, extracted the UNSW crest and adapted its cover hierarchy for an
individual FINS5545 submission. It identified that Figures A1-A8 existed but
were not all explicitly referenced in the narrative, and that the required
sentiment-fusion before/after evidence had a figure and CSV but no report table.
It added the missing fusion table, cross-referenced and interpreted every
appendix exhibit, corrected terminology such as expanding window, sector-level
tilt and covariance shrinkage, and repaired corrupted punctuation in the
references. The final report contains 2,654 narrative words, seven narrative
pages and 14 pages including cover, appendices and references.

### What was wrong or risky

The reference cover belonged to a different course and a group submission, so
copying its text literally would have introduced false course and authorship
information. During the first automated Word edit, a generic text-replacement
loop also assigned empty text to picture and page-break runs. This removed the
embedded figures and cover page break even though the document still opened.
The error was visible only after rendering the DOCX. A second visual issue came
from separate even-page headers and footers, which placed some page numbers
partly outside the page. The report also could not honestly state that the app
was live because no Streamlit URL had been verified.

### What I changed and why

I used the uploaded PDF only as a layout reference and retained the correct
course, zID, individual-project title and sample dates. I restored the DOCX from
the pre-edit backup, changed the script so it edits a run only when its text
actually changes, and left picture and page-break XML untouched. I disabled the
inconsistent even-page header/footer setting and regenerated the document. All
14 pages were rendered to images and checked for figure loss, clipping, table
overflow, captions, headers, footers and page numbering before the matching PDF
was replaced. The report states the confirmed public repository but leaves the
live Streamlit URL as an explicit outstanding submission requirement.

---

## 9. Close the final delivery gaps and prepare the hand-in (14 August 2026)

### What I wanted

Finish every remaining Project B item that could be completed locally: remove
stale submission wording, protect the final student-edited report, rebuild from
a clean results directory, run all tests, verify the app and public repository,
and prepare the exact Moodle archive. The live Streamlit deployment should be
attempted but not falsely reported if authentication prevented completion.

### Prompt(s)

> "Help me complete all remaining content for Project B."

> "Treat the project as a final submission: reconcile the report, AI log,
> generated evidence, app, repository and submission checklist, then verify the
> result rather than assuming earlier checks still apply."

### What the assistant produced

The assistant updated the README, completion matrix, submission checklist and QA
addendum to reflect the final 28-file build, completed human review, six-page app
and public repository. It changed `scripts/build_report.py` to write an ignored
`report_generated_draft.docx`, then ran it and confirmed the SHA-256 of the final
student-edited `report/report.docx` was unchanged. A clean rebuild recreated
10,392 fund-return rows, 17,280 weight rows, 20,120 sector-index rows, 12 fund
metrics and all 28 expected result files. The four required hashes matched the
final QA record. All 50 headline labels and all 24 reviewed lexicon decisions
were restored automatically.

The full suite passed 13 tests, the separate real-data no-look-ahead audit passed
all 12 funds and 36 rebalances per fund, and `scripts/check_handin.py` passed 23
checks with no warnings after generated caches were removed. A real local
Streamlit server returned HTTP 200 and health body `ok`, and no listener remained
after the check. GitHub was confirmed as public on `main`. Streamlit Community
Cloud opened at its sign-in page, but the available controlled browser did not
share the student's authenticated session.

### What was wrong or risky

Several files still described an older state: a private repository, 21 generated
outputs, incomplete human review and an AI draft that the student still had to
rewrite. More importantly, the report generator still targeted the final Word
file, so a routine reproducibility command could erase the student's manual
financial-language edits and new cover. The first clean rebuild also exposed an
external compatibility issue: the course ZIP could be downloaded, but Anaconda's
`pyarrow 19` raised `Repetition level histogram size mismatch`. Editing the frozen
loader or preserving the deleted results without a clean build would both have
weakened the audit. Finally, local HTTP success is not equivalent to a public
Streamlit deployment, and bypassing or pretending to complete account sign-in
would be dishonest.

### What I changed and why

I separated reproducible draft generation from the final authored report and
verified this protection by hash. I did not modify `src/data_access.py`; instead,
I reran the same official pipeline in the existing project environment with
`pyarrow 24`, temporarily selecting the backup URL already specified by the
frozen loader. This completed successfully and reproduced the recorded required
hashes. I removed generated Python caches only after testing, reran the official
checker, and used the verified Git snapshot to prepare the Moodle archive. The
Streamlit sign-in page was left as an explicit handoff: deployment can be claimed
complete only after the student authenticates and the resulting public URL opens
in a logged-out browser.
