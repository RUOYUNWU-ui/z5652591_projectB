# Student manual sentiment review

The student completed this evidence step on 2026-08-14. The saved labels remain
independent human judgements; the model scores are retained only for comparison.

## Completed file

Open `results/tables/sentiment_manual_review_template.csv`. It contains 50
headlines sampled reproducibly at five per equity sector. Do not change the
headline, score, ID, date, ticker, or sector columns.

Every row contains:

- `student_label`: exactly `negative`, `neutral`, or `positive`.
- `student_confidence`: an integer from 1 (uncertain) to 5 (very certain).
- `student_notes`: a short reason, especially where financial language,
  negation, ambiguity, or irony affects the judgement.
- `review_complete`: change to `True` only after reviewing that row yourself.

Judge the headline text without looking at future returns. The aim is model
validity, not whether the news predicted the market.

## Validate and produce the report table

From the project root, run:

```powershell
python scripts/validate_sentiment_review.py
```

The validator refuses partial or invalid labels. The completed review writes
`results/tables/sentiment_manual_review_validation.csv`, comparing human
agreement with plain and finance-enhanced VADER. The observed overall agreement
is 66% for plain VADER and 70% for enhanced VADER; this modest gain and the weak
negative-class agreement are both reported rather than presenting a blanket
accuracy claim.

Keep the completed template and validation CSV in the submission. Before writing
the generated template, `scripts/run_part_b.py` now saves the human-only fields
to `report/sentiment_manual_review_annotations.json`. A clean rebuild restores
the labels from that file and re-runs validation, preventing accidental loss.
