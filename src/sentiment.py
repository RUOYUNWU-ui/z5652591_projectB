"""VADER headline scoring and sector sentiment-index construction.

Part A preserves raw title casing, punctuation and negation. This module uses
that text unchanged: no lowercasing, stopword removal or punctuation stripping
occurs before VADER scoring.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd


# AI proposed the initial terms and scores; the student reviewed and accepted
# all 24 entries on 2026-08-14, revising the rationales below. Scores use
# VADER's usual -4..+4 valence range. This is a small, explainable finance
# extension, not a copy of the full Loughran-McDonald dictionary.
FINANCE_LEXICON_CANDIDATES: tuple[dict[str, object], ...] = (
    {"term": "beat", "score": 2.0, "rationale": "Results exceed expectations; positive signal.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "beats", "score": 2.0, "rationale": "Third-person/plural form of beat; results beat expectations.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "miss", "score": -2.0, "rationale": "Results fall short of expectations; negative signal.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "misses", "score": -2.0, "rationale": "Third-person/plural form of miss; results miss expectations.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "upgrade", "score": 2.2, "rationale": "Analyst/rating upgrade; generally favourable for asset prices.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "upgraded", "score": 2.2, "rationale": "Past tense/participle of upgrade; rating has been raised.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "downgrade", "score": -2.2, "rationale": "Analyst/rating downgrade; generally adverse for asset prices.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "downgraded", "score": -2.2, "rationale": "Past tense/participle of downgrade; rating has been lowered.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "outperform", "score": 1.8, "rationale": "Performs better than benchmark/market; positive rating.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "outperforms", "score": 1.8, "rationale": "Third-person form of outperform; beats benchmark.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "underperform", "score": -1.8, "rationale": "Performs worse than benchmark/market; negative rating.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "underperforms", "score": -1.8, "rationale": "Third-person form of underperform; lags benchmark.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "bullish", "score": 2.0, "rationale": "Expresses positive market outlook; clearly favourable.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "bearish", "score": -2.0, "rationale": "Expresses negative market outlook; clearly adverse.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "buyback", "score": 1.5, "rationale": "Share repurchase signals confidence and supports value; occasionally driven by other motives, but broadly positive.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "buybacks", "score": 1.5, "rationale": "Plural form of buyback; multiple or ongoing repurchases.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "surges", "score": 2.3, "rationale": "Sharp rise in price or operating metrics; strongly positive.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Positive"},
    {"term": "plunges", "score": -2.5, "rationale": "Sharp, steep drop in price or results; strongly negative.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "selloff", "score": -2.2, "rationale": "Broad or concentrated selling pressure leading to price falls; negative.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "bankruptcy", "score": -3.2, "rationale": "Legal state of insolvency; extreme negative event.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "bankrupt", "score": -3.2, "rationale": "Financially insolvent; unable to pay debts; severe distress.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "insolvency", "score": -3.0, "rationale": "Inability to meet financial obligations; severe distress, slightly less severe than bankruptcy.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "delisting", "score": -2.5, "rationale": "Removal or threatened removal from exchange listing; major negative.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
    {"term": "slashes", "score": -2.2, "rationale": "Deep cuts to guidance, workforce, or payouts; clearly adverse.", "review_status": "Reviewed", "final_decision": "Accept", "final_valence": "Negative"},
)

FINANCE_LEXICON = {
    str(item["term"]): float(item["score"])
    for item in FINANCE_LEXICON_CANDIDATES
}


def finance_lexicon_table() -> pd.DataFrame:
    """Return the student-reviewed finance lexicon and audit decisions."""
    return pd.DataFrame(FINANCE_LEXICON_CANDIDATES)


def ensure_vader_lexicon(download: bool = False) -> None:
    """Verify VADER data exists, optionally downloading it as a build step.

    The deployed Streamlit app never calls this function. ``run_part_b.py``
    may call it once before the offline sentiment build.
    """
    import nltk

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        if not download:
            raise LookupError(
                "VADER lexicon is missing. Run the offline build with "
                "ensure_vader_lexicon(download=True)."
            )
        success = nltk.download("vader_lexicon", quiet=True)
        if not success:
            raise RuntimeError("nltk could not download vader_lexicon")
        nltk.data.find("sentiment/vader_lexicon.zip")


def _analyser(lexicon_extension: Mapping[str, float] | None = None):
    ensure_vader_lexicon(download=False)
    from nltk.sentiment import SentimentIntensityAnalyzer

    analyser = SentimentIntensityAnalyzer()
    if lexicon_extension:
        cleaned = {str(term).lower(): float(score) for term, score in lexicon_extension.items()}
        if any(not np.isfinite(score) or abs(score) > 4 for score in cleaned.values()):
            raise ValueError("Finance lexicon scores must be finite and within [-4, 4]")
        analyser.lexicon.update(cleaned)
    return analyser


def _headline_rows(panel: pd.DataFrame) -> pd.DataFrame:
    """Normalise raw-row or Part-A assembled-panel input without editing text."""
    if not isinstance(panel, pd.DataFrame) or panel.empty:
        raise ValueError("panel must be a non-empty pandas DataFrame")
    frame = panel.copy()
    date_column = "trading_day" if "trading_day" in frame.columns else "date"
    required = {date_column, "ticker", "sector"}
    if not required.issubset(frame.columns):
        raise ValueError(f"panel is missing required columns: {sorted(required - set(frame))}")

    if "title" in frame.columns:
        rows = frame[[date_column, "ticker", "sector", "title"]].copy()
    elif "headlines" in frame.columns:
        rows = frame[[date_column, "ticker", "sector", "headlines"]].explode(
            "headlines", ignore_index=True
        )
        rows = rows.rename(columns={"headlines": "title"})
    else:
        raise ValueError("panel needs either a raw 'title' or assembled 'headlines' column")

    rows = rows.dropna(subset=[date_column, "ticker", "sector", "title"]).copy()
    rows["date"] = (
        pd.to_datetime(rows[date_column], utc=True).dt.tz_localize(None).dt.normalize()
    )
    rows["title"] = rows["title"].astype(str)
    rows = rows[["date", "ticker", "sector", "title"]].reset_index(drop=True)
    # Exact headlines were deduplicated on their original publication dates in
    # Part A. Distinct weekend/holiday rows can nevertheless map onto the same
    # trading day and then share date+ticker+title. Keep a stable occurrence ID
    # rather than incorrectly deduplicating valid mapped observations again.
    rows.insert(0, "headline_id", np.arange(len(rows), dtype="int64"))
    return rows


def score_individual_headlines(
    panel: pd.DataFrame,
    lexicon_extension: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Score every original headline and retain its raw text for review."""
    rows = _headline_rows(panel)
    analyser = _analyser(lexicon_extension)
    unique_titles = rows["title"].unique()
    score_map = {
        title: float(analyser.polarity_scores(title)["compound"])
        for title in unique_titles
    }
    rows["sentiment"] = rows["title"].map(score_map).astype(float)
    rows["model"] = "vader_finance_enhanced" if lexicon_extension else "vader_plain"
    return rows


def _aggregate_ticker_days(headline_scores: pd.DataFrame) -> pd.DataFrame:
    return (
        headline_scores.groupby(
            ["date", "ticker", "sector", "model"], sort=True, dropna=False
        )
        .agg(sentiment=("sentiment", "mean"), n_headlines=("title", "size"))
        .reset_index()
        .assign(news_available=True)
    )


def score_headlines(
    panel: pd.DataFrame,
    lexicon_extension: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Score raw titles with VADER and aggregate to ticker-day sentiment.

    ``lexicon_extension=None`` is the plain-VADER baseline. Supplying the
    reviewed finance dictionary runs the enhanced model through the same code
    path, making the comparison attributable only to the lexicon change.
    """
    return _aggregate_ticker_days(
        score_individual_headlines(panel, lexicon_extension=lexicon_extension)
    )


def sector_sentiment_index(
    scores: pd.DataFrame,
    trading_calendar: Sequence[pd.Timestamp] | pd.Index | None = None,
) -> pd.DataFrame:
    """Build an equal-weight ticker sector index on the equity calendar.

    Missing ticker-days are not imputed as neutral. A sector-day with no
    ticker news is retained with ``news_available=False``, zero coverage
    counts, and ``sentiment=NaN``. ``sentiment_lag1`` is the prior trading
    day's value within sector and model, so it is safe to use no earlier than
    the following trading day.
    """
    required = {"date", "ticker", "sector", "sentiment", "n_headlines"}
    missing = required - set(scores.columns)
    if missing:
        raise ValueError(f"scores is missing required columns: {sorted(missing)}")
    frame = scores.copy()
    frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.tz_localize(None).dt.normalize()
    if "model" not in frame:
        frame["model"] = "unspecified"

    grouped = (
        frame.groupby(["model", "date", "sector"], sort=True, dropna=False)
        .agg(
            sentiment=("sentiment", "mean"),
            n_tickers=("ticker", "nunique"),
            n_headlines=("n_headlines", "sum"),
        )
        .reset_index()
    )
    if trading_calendar is None:
        dates = pd.DatetimeIndex(frame["date"].dropna().unique()).sort_values()
    else:
        dates = (
            pd.DatetimeIndex(pd.to_datetime(trading_calendar, utc=True))
            .tz_localize(None)
            .normalize()
            .unique()
            .sort_values()
        )
    sectors = pd.Index(frame["sector"].dropna().unique()).sort_values()
    models = pd.Index(frame["model"].dropna().unique()).sort_values()
    if dates.empty or sectors.empty or models.empty:
        raise ValueError("scores must contain dates, sectors and model labels")

    grid = pd.MultiIndex.from_product(
        [models, dates, sectors], names=["model", "date", "sector"]
    ).to_frame(index=False)
    index = grid.merge(grouped, on=["model", "date", "sector"], how="left")
    index["n_tickers"] = index["n_tickers"].fillna(0).astype(int)
    index["n_headlines"] = index["n_headlines"].fillna(0).astype(int)
    index["news_available"] = index["n_tickers"].gt(0)
    index = index.sort_values(["model", "sector", "date"], kind="stable")
    index["sentiment_lag1"] = index.groupby(
        ["model", "sector"], sort=False
    )["sentiment"].shift(1)
    return index[
        [
            "date", "sector", "sentiment", "sentiment_lag1",
            "n_tickers", "n_headlines", "news_available", "model",
        ]
    ].sort_values(["date", "sector", "model"], kind="stable").reset_index(drop=True)


def compare_vader_models(
    panel: pd.DataFrame,
    trading_calendar: Sequence[pd.Timestamp] | pd.Index | None = None,
    sample_per_sector: int = 5,
    random_state: int = 5545,
) -> dict[str, pd.DataFrame]:
    """Compare plain/enhanced VADER and create a stratified review sample."""
    if sample_per_sector < 1:
        raise ValueError("sample_per_sector must be positive")
    plain_headlines = score_individual_headlines(panel)
    enhanced_headlines = score_individual_headlines(panel, FINANCE_LEXICON)
    keys = ["headline_id", "date", "ticker", "sector", "title"]
    comparison = plain_headlines[keys + ["sentiment"]].rename(
        columns={"sentiment": "plain_score"}
    ).merge(
        enhanced_headlines[keys + ["sentiment"]].rename(
            columns={"sentiment": "enhanced_score"}
        ),
        on=keys,
        how="inner",
        validate="one_to_one",
    )
    summary = pd.DataFrame(
        [
            {
                "model": "vader_plain",
                "n_headlines": len(comparison),
                "neutral_rate": float(comparison["plain_score"].between(-0.05, 0.05).mean()),
            },
            {
                "model": "vader_finance_enhanced",
                "n_headlines": len(comparison),
                "neutral_rate": float(comparison["enhanced_score"].between(-0.05, 0.05).mean()),
            },
        ]
    )

    sector_counts = comparison.groupby("sector").size()
    too_small = sector_counts[sector_counts < sample_per_sector]
    if not too_small.empty:
        raise ValueError(f"Not enough headlines to sample in sectors: {too_small.to_dict()}")
    review_sample = (
        comparison.groupby("sector", group_keys=False, sort=True)
        .sample(n=sample_per_sector, random_state=random_state)
        .sort_values(["sector", "date", "ticker"], kind="stable")
        .reset_index(drop=True)
    )

    plain_ticker = _aggregate_ticker_days(plain_headlines)
    enhanced_ticker = _aggregate_ticker_days(enhanced_headlines)
    sector_index = pd.concat(
        [
            sector_sentiment_index(plain_ticker, trading_calendar),
            sector_sentiment_index(enhanced_ticker, trading_calendar),
        ],
        ignore_index=True,
    ).sort_values(["date", "sector", "model"], kind="stable").reset_index(drop=True)
    return {
        "summary": summary,
        "review_sample": review_sample,
        "headline_comparison": comparison,
        "plain_ticker_scores": plain_ticker,
        "enhanced_ticker_scores": enhanced_ticker,
        "sector_index": sector_index,
        "lexicon_candidates": finance_lexicon_table(),
    }
