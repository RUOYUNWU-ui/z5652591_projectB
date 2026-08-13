"""Tests and real-data acceptance audit for sentiment-weight fusion."""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.fusion import apply_sentiment, evaluate_fusion_variants  # noqa: E402


def _synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar = pd.bdate_range("2022-01-03", periods=100)
    effective_dates = calendar[[65, 85]]
    weights = pd.DataFrame(
        [
            {
                "rebalance_date": calendar[calendar.get_loc(date) - 1],
                "effective_date": date,
                "ticker": ticker,
                "asset_class": "equity",
                "sector": sector,
                "weight": weight,
            }
            for date in effective_dates
            for ticker, sector, weight in [
                ("AAA", "Tech", 0.35), ("BBB", "Tech", 0.15),
                ("CCC", "Energy", 0.30), ("DDD", "Energy", 0.20),
            ]
        ]
    )
    values = np.sin(np.arange(len(calendar)) / 7.0) * 0.2
    sentiment = pd.concat(
        [
            pd.DataFrame(
                {
                    "date": calendar,
                    "sector": sector,
                    "sentiment": values * sign,
                    "sentiment_lag1": pd.Series(values * sign).shift(1),
                    "model": "test",
                }
            )
            for sector, sign in [("Tech", 1.0), ("Energy", -1.0)]
        ],
        ignore_index=True,
    )
    return weights, sentiment


def test_lambda_zero_and_constraints() -> None:
    weights, sentiment = _synthetic_inputs()
    zero = apply_sentiment(weights, sentiment, 0, window=40, min_periods=20)
    assert np.array_equal(zero["weight"].to_numpy(), zero["base_weight"].to_numpy())
    for lam in (1.0, -1.0):
        tilted = apply_sentiment(weights, sentiment, lam, window=40, min_periods=20)
        sums = tilted.groupby("effective_date")["weight"].sum()
        assert np.allclose(sums, 1.0, atol=1e-10)
        assert (tilted["weight"] >= 0).all()
        used = tilted["signal_available"]
        assert (
            tilted.loc[used, "sentiment_source_date"]
            < tilted.loc[used, "effective_date"]
        ).all()


def verify_real_data() -> None:
    from src.etl import load_clean_equities
    from src.features import daily_returns
    from src.portfolios import oos_backtest

    sentiment_path = ROOT / "results" / "data" / "sector_sentiment_index.csv"
    if not sentiment_path.exists():
        raise FileNotFoundError(
            "Run tests/test_sentiment.py --real before the fusion acceptance audit"
        )
    sentiment = pd.read_csv(sentiment_path, parse_dates=["date"])
    sentiment = sentiment.loc[sentiment["model"].eq("vader_finance_enhanced")].copy()

    equities, _, _, _ = load_clean_equities()
    sector_map = equities[["ticker", "sector"]].drop_duplicates("ticker")
    equity_returns = daily_returns(equities).merge(sector_map, on="ticker", how="left")
    equity_returns["asset_class"] = "equity"
    base = oos_backtest(equity_returns, "min_variance")
    comparison = evaluate_fusion_variants(
        base["weights"], equity_returns, sentiment, window=60, min_periods=20
    )

    zero = comparison["weights"]["base"]
    assert np.array_equal(zero["weight"].to_numpy(), zero["base_weight"].to_numpy())
    for name in ("momentum", "contrarian"):
        tilted = comparison["weights"][name]
        assert np.allclose(
            tilted.groupby("effective_date")["weight"].sum(), 1.0, atol=1e-10
        )
        used = tilted["signal_available"]
        assert (
            tilted.loc[used, "sentiment_source_date"]
            < tilted.loc[used, "effective_date"]
        ).all()

    table_dir = ROOT / "results" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    comparison["metrics"].to_csv(table_dir / "fusion_comparison.csv", index=False)
    for name, daily in comparison["returns"].items():
        daily.to_csv(ROOT / "results" / "data" / f"fusion_returns_{name}.csv", index=False)

    print(comparison["metrics"].to_string(index=False))
    print(
        "signal_rows_used="
        + str(int(comparison["weights"]["momentum"]["signal_available"].sum()))
    )
    print(
        "first_sentiment_source="
        + str(comparison["weights"]["momentum"]["sentiment_source_date"].dropna().min().date())
    )
    print(
        "first_tilt_effective="
        + str(comparison["weights"]["momentum"]["effective_date"].min().date())
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    test_lambda_zero_and_constraints()
    print("lambda=0, full-investment and lag invariants: PASS")
    if args.real:
        verify_real_data()
        print("real-data fusion acceptance checks: PASS")
