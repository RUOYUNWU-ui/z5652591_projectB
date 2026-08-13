# SignalYield - FINS5545 Project B

Part B: funds, sentiment, and the app (DFF Stations 3-4). This folder is also your
public GitHub repository; the app entrypoint is streamlit_app.py at the root.

## How to run

    pip install -r requirements.txt -r requirements-dev.txt
    python scripts/run_part_b.py            # reproduces your results into results/
    python scripts/build_report.py           # optional draft; does not overwrite the final report
    python scripts/validate_sentiment_review.py  # after student labels 50 headlines
    streamlit run streamlit_app.py          # runs the app locally

Load raw data through src/data_access.py (see context/DATA_GUIDE.md); never commit
raw data. The deployed app, by contrast, reads your precomputed artifacts from
results/ - those ARE committed.

## What is here

- streamlit_app.py    the app entrypoint (repo root)
- .streamlit/         app config
- PROJECT_BRIEF.md    the full assignment brief for your course (read this first)
- src/                data, portfolios, sentiment, fusion, and robustness code
- scripts/            runnable scripts that reproduce your results
- results/            your outputs: figures in results/figures/, tables in results/tables/, app data artifacts in results/data/
- context/            provided data guide and project context (do not edit)
- report/             editable Word report, PDF, QA record, and student-review instructions
- ai/                 your prompt logs and AI notes
- requirements-dev.txt build/repro-only dependencies; excluded from app deployment
- AGENTS.md / CLAUDE.md project-specific AI instructions

## Research design

- 12 canonical funds: equity, crypto, and combined universes crossed with equal
  weight, minimum variance, maximum Sharpe, and risk parity.
- Monthly expanding-window OOS weights take effect on the next trading day.
- Finance-enhanced VADER sector index and fixed base/momentum/contrarian fusion.
- Separately labelled robustness: Ledoit-Wolf covariance shrinkage and a
  0/10/25/50/100 bps transaction-cost curve.
- Six-page investor app, including a Robustness Lab. The app reads only
  precomputed `results/` artifacts.

The baseline assumes a zero risk-free rate and zero transaction costs. The
cost curve is a sensitivity analysis, not a silently substituted baseline.

## Deploy + hand in

This folder is its own GitHub repo. The automated build, tests, report, and
precomputed artifacts are committed here. See
PROJECT_BRIEF.md Appendix D and docs/STUDENT_DEPLOY.md (in this folder). In short:

    python scripts/check_handin.py        # your agent can run this
    # commit your precomputed app artifacts under results/ (the app reads them)
    # commit and push the precomputed artifacts

The public repository is:

    https://github.com/RUOYUNWU-ui/z5652591_projectB

The 50-headline and 24-term reviews are complete and preserved by the build.
The final student-edited report is `report/report.docx`, with the submission PDF
at `report/report.pdf`. `scripts/build_report.py` intentionally writes
`report/report_generated_draft.docx` so a reproducible AI/evidence draft cannot
overwrite the student's final Word source. Before hand-in, confirm the live
Streamlit URL in a logged-out browser, submit both URLs, and upload the final zip
to Moodle.
