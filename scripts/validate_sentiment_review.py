"""Validate the student's 50-headline manual sentiment review.

The pipeline creates ``results/tables/sentiment_manual_review_template.csv``.
The student completes the four ``student_*``/``review_complete`` columns and
runs this script. Human labels are deliberately never inferred or filled by AI.
"""
from __future__ import annotations

import argparse
import pathlib

import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "results" / "tables" / "sentiment_manual_review_template.csv"
DEFAULT_OUTPUT = ROOT / "results" / "tables" / "sentiment_manual_review_validation.csv"
VALID_LABELS = {"negative", "neutral", "positive"}


def _score_label(score: pd.Series) -> pd.Series:
    return pd.Series(
        pd.cut(
            score,
            bins=[float("-inf"), -0.05, 0.05, float("inf")],
            labels=["negative", "neutral", "positive"],
            right=False,
        ).astype("string"),
        index=score.index,
    )


def validate(input_path: pathlib.Path, output_path: pathlib.Path) -> pd.DataFrame:
    """Validate completed labels and write plain/enhanced agreement statistics."""
    frame = pd.read_csv(input_path)
    required = {
        "headline_id", "student_label", "student_confidence", "student_notes",
        "review_complete", "plain_score", "enhanced_score",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Review file is missing columns: {sorted(missing)}")
    if len(frame) != 50:
        raise ValueError(f"Expected the stratified 50-headline sample, found {len(frame)}")

    complete = frame["review_complete"].astype(str).str.lower().eq("true")
    if not complete.all():
        raise ValueError(
            f"Manual review is incomplete: {int((~complete).sum())} rows remain. "
            "Set review_complete=True only after making your own judgement."
        )
    labels = frame["student_label"].astype(str).str.strip().str.lower()
    invalid = sorted(set(labels) - VALID_LABELS)
    if invalid:
        raise ValueError(
            "student_label must be negative, neutral, or positive; invalid: "
            + ", ".join(invalid)
        )

    confidence = pd.to_numeric(frame["student_confidence"], errors="coerce")
    if confidence.isna().any() or not confidence.between(1, 5).all():
        raise ValueError("student_confidence must be an integer from 1 to 5")

    frame["student_label"] = labels
    frame["plain_label"] = _score_label(frame["plain_score"])
    frame["enhanced_label"] = _score_label(frame["enhanced_score"])
    rows = []
    for model in ("plain", "enhanced"):
        predicted = frame[f"{model}_label"]
        rows.append(
            {
                "model": f"vader_{model}",
                "n_reviewed": len(frame),
                "agreement_rate": float(predicted.eq(labels).mean()),
                "negative_agreement": float(
                    predicted[labels.eq("negative")].eq("negative").mean()
                ),
                "neutral_agreement": float(
                    predicted[labels.eq("neutral")].eq("neutral").mean()
                ),
                "positive_agreement": float(
                    predicted[labels.eq("positive")].eq("positive").mean()
                ),
                "mean_student_confidence": float(confidence.mean()),
            }
        )
    summary = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    summary = validate(args.input, args.output)
    print(summary.to_string(index=False))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
