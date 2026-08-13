# Student manual sentiment review

This is the only remaining evidence step that must be completed by the student,
because the project brief requires the written interpretation to be the
student's own and an AI-generated label would not be an independent manual
check.

## File to complete

Open `results/tables/sentiment_manual_review_template.csv`. It contains 50
headlines sampled reproducibly at five per equity sector. Do not change the
headline, score, ID, date, ticker, or sector columns.

For every row, complete:

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

The validator refuses partial or invalid labels. When all 50 rows are complete,
it writes `results/tables/sentiment_manual_review_validation.csv`, comparing
human agreement with plain and finance-enhanced VADER. Interpret that result in
your own words in the final report; do not claim the enhanced model is better
unless the completed evidence supports it.

Keep the completed template and validation CSV in the submission. Re-running
`scripts/run_part_b.py` recreates a blank template, so make a backup before a
clean rebuild.
