"""Tests and real-data acceptance audit for the Part B sentiment model."""
from __future__ import annotations

import argparse
import pathlib
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.run_part_b as runner  # noqa: E402
from src.sentiment import (  # noqa: E402
    compare_vader_models,
    ensure_vader_lexicon,
    sector_sentiment_index,
)


def test_no_news_and_lag_are_explicit() -> None:
    scores = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-02", "2023-01-04"]),
            "ticker": ["AAA", "AAA"],
            "sector": ["Tech", "Tech"],
            "sentiment": [0.4, -0.2],
            "n_headlines": [2, 1],
            "model": ["test", "test"],
        }
    )
    calendar = pd.to_datetime(["2023-01-02", "2023-01-03", "2023-01-04"])
    index = sector_sentiment_index(scores, calendar)
    middle = index.loc[index["date"].eq(pd.Timestamp("2023-01-03"))].iloc[0]
    final = index.loc[index["date"].eq(pd.Timestamp("2023-01-04"))].iloc[0]
    assert not bool(middle["news_available"])
    assert np.isnan(middle["sentiment"])
    assert middle["sentiment_lag1"] == 0.4
    assert np.isnan(final["sentiment_lag1"])


def test_manual_review_annotations_survive_clean_rebuild(monkeypatch) -> None:
    local_tmp_root = ROOT / "tmp"
    local_tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_path = pathlib.Path(tempfile.mkdtemp(prefix="review_test_", dir=local_tmp_root))
    template_path = tmp_path / "results" / "sentiment_manual_review_template.csv"
    backup_path = tmp_path / "report" / "sentiment_manual_review_annotations.json"
    template_path.parent.mkdir(parents=True)
    sample = pd.DataFrame(
        [{
            "headline_id": 7, "date": "2023-01-03", "ticker": "AAA",
            "sector": "Tech", "title": "AAA beats expectations",
            "plain_score": 0.0, "enhanced_score": 0.5,
        }]
    )
    completed = sample.assign(
        student_label="positive", student_confidence=5,
        student_notes="Human judgement", review_complete=True,
    )
    completed.to_csv(template_path, index=False)
    monkeypatch.setattr(runner, "MANUAL_REVIEW_TEMPLATE", template_path)
    monkeypatch.setattr(runner, "MANUAL_REVIEW_BACKUP", backup_path)

    try:
        first = runner._prepare_manual_review_template(sample)
        assert backup_path.exists()
        assert first.loc[0, "student_label"] == "positive"
        template_path.unlink()
        restored = runner._prepare_manual_review_template(sample)
        assert restored.loc[0, "student_label"] == "positive"
        assert int(restored.loc[0, "student_confidence"]) == 5
        assert runner._truthy(restored.loc[0, "review_complete"])
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def verify_real_data() -> None:
    from src import data_access
    from src.calendar_merge import dedupe_news_headlines, map_headline_to_trading_day
    from src.etl import load_clean_equities
    from src.features import assemble_headline_panel

    ensure_vader_lexicon(download=True)
    equities, _, _, _ = load_clean_equities()
    news, duplicates = dedupe_news_headlines(data_access.load_news_headlines())
    calendar = pd.DatetimeIndex(equities["date"].unique()).sort_values()
    mapped, after_calendar = map_headline_to_trading_day(news, calendar)
    panel = assemble_headline_panel(mapped)
    result = compare_vader_models(panel, calendar, sample_per_sector=5)

    summary = result["summary"].set_index("model")
    plain_rate = float(summary.loc["vader_plain", "neutral_rate"])
    enhanced_rate = float(summary.loc["vader_finance_enhanced", "neutral_rate"])
    index = result["sector_index"]
    sample = result["review_sample"]

    assert index["sector"].nunique() == 10
    assert (~index["news_available"]).any()
    assert enhanced_rate < plain_rate
    assert len(sample) == index["sector"].nunique() * 5
    assert sample.groupby("sector").size().eq(5).all()

    data_dir = ROOT / "results" / "data"
    table_dir = ROOT / "results" / "tables"
    data_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    result["sector_index"].to_csv(data_dir / "sector_sentiment_index.csv", index=False)
    result["summary"].to_csv(table_dir / "sentiment_model_comparison.csv", index=False)
    result["review_sample"].to_csv(table_dir / "sentiment_manual_review_sample.csv", index=False)
    result["lexicon_candidates"].to_csv(table_dir / "finance_lexicon_candidates.csv", index=False)

    print(f"news_duplicates_dropped={duplicates}")
    print(f"news_after_calendar_dropped={after_calendar}")
    print(f"headline_panel_rows={len(panel)}")
    print(f"plain_neutral_rate={plain_rate:.6%}")
    print(f"enhanced_neutral_rate={enhanced_rate:.6%}")
    print(f"neutral_rate_change_pp={(enhanced_rate - plain_rate) * 100:.4f}")
    print(f"sector_count={index['sector'].nunique()}")
    print(f"sector_index_rows={len(index)}")
    print(f"no_news_rows={int((~index['news_available']).sum())}")
    print(f"review_sample_rows={len(sample)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    test_no_news_and_lag_are_explicit()
    print("no-news distinction and one-day lag: PASS")
    if args.real:
        verify_real_data()
        print("real-data sentiment acceptance checks: PASS")
