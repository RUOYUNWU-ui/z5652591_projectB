"""Look-ahead-safe fusion of sector sentiment and portfolio weights."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.portfolios import performance_metrics


def _sentiment_zscores(
    sentiment: pd.DataFrame,
    window: int,
    min_periods: int,
) -> pd.DataFrame:
    required = {"date", "sector", "sentiment_lag1"}
    missing = required - set(sentiment.columns)
    if missing:
        raise ValueError(f"sentiment is missing required columns: {sorted(missing)}")
    if window < 2 or min_periods < 2 or min_periods > window:
        raise ValueError("Require 2 <= min_periods <= window")

    frame = sentiment.copy()
    if "model" in frame.columns and frame["model"].nunique(dropna=True) > 1:
        raise ValueError("Filter sentiment to exactly one model before fusion")
    frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.tz_localize(None).dt.normalize()
    frame = frame.sort_values(["sector", "date"], kind="stable").reset_index(drop=True)

    # sentiment_lag1 at trade date t contains sector news from trading day t-1.
    # The historical mean/std are shifted once more, so the current lagged
    # observation is compared only with values known before it.
    grouped = frame.groupby("sector", sort=False)["sentiment_lag1"]
    frame["rolling_mean"] = grouped.transform(
        lambda s: s.shift(1).rolling(window, min_periods=min_periods).mean()
    )
    frame["rolling_std"] = grouped.transform(
        lambda s: s.shift(1).rolling(window, min_periods=min_periods).std(ddof=1)
    )
    frame["z_score"] = (
        frame["sentiment_lag1"] - frame["rolling_mean"]
    ).div(frame["rolling_std"].replace(0.0, np.nan))
    frame["signal_available"] = frame[
        ["sentiment_lag1", "rolling_mean", "rolling_std", "z_score"]
    ].notna().all(axis=1)
    # No usable signal means no tilt. This is operationally z=0 while the
    # signal_available flag preserves the distinction from observed neutrality.
    frame["z_score"] = frame["z_score"].fillna(0.0)
    frame["sentiment_source_date"] = frame.groupby("sector", sort=False)["date"].shift(1)
    frame.loc[~frame["signal_available"], "sentiment_source_date"] = pd.NaT
    return frame[
        [
            "date", "sector", "sentiment_lag1", "rolling_mean", "rolling_std",
            "z_score", "signal_available", "sentiment_source_date",
        ]
    ]


def apply_sentiment(
    weights: pd.DataFrame,
    sentiment: pd.DataFrame,
    lam: float,
    window: int = 60,
    min_periods: int = 20,
) -> pd.DataFrame:
    """Apply the frozen multiplicative sentiment tilt to equity weights.

    The exact rule is ``w_tilde = w_base * (1 + lam * z)`` followed by
    clipping negative equity weights to zero and renormalising them back to
    the base fund's total equity exposure. Crypto/non-equity weights are left
    unchanged. ``lam=0`` reproduces base weights exactly.

    The 60-trading-day window (minimum 20 historical observations) is a
    pre-result, untuned implementation choice approximating one quarter. Both
    ``lam=+1`` and ``lam=-1`` are evaluated once; this function performs no
    selection or tuning against the OOS result.
    """
    required = {"effective_date", "ticker", "weight", "sector"}
    missing = required - set(weights.columns)
    if missing:
        raise ValueError(f"weights is missing required columns: {sorted(missing)}")
    if not np.isfinite(lam):
        raise ValueError("lam must be finite")

    base = weights.copy()
    base["effective_date"] = (
        pd.to_datetime(base["effective_date"], utc=True).dt.tz_localize(None).dt.normalize()
    )
    if "asset_class" not in base.columns:
        base["asset_class"] = np.where(base["sector"].notna(), "equity", "crypto")
    if base.duplicated(["effective_date", "ticker"]).any():
        raise ValueError("weights contains duplicate effective_date-ticker rows")
    if (base["weight"] < -1e-12).any():
        raise ValueError("base weights must be long-only")

    zscores = _sentiment_zscores(sentiment, window=window, min_periods=min_periods)
    merged = base.rename(columns={"weight": "base_weight"}).merge(
        zscores,
        left_on=["effective_date", "sector"],
        right_on=["date", "sector"],
        how="left",
        validate="many_to_one",
    )
    merged = merged.drop(columns=["date"])
    merged["z_score"] = merged["z_score"].fillna(0.0)
    merged["signal_available"] = merged["signal_available"].fillna(False).astype(bool)
    merged["lambda"] = float(lam)
    merged["raw_tilted_weight"] = merged["base_weight"]
    merged["weight"] = merged["base_weight"]

    equity_mask = merged["asset_class"].astype(str).str.lower().eq("equity")
    if lam != 0:
        merged.loc[equity_mask, "raw_tilted_weight"] = (
            merged.loc[equity_mask, "base_weight"]
            * (1.0 + float(lam) * merged.loc[equity_mask, "z_score"])
        ).clip(lower=0.0)

        for effective_date, positions in merged.groupby("effective_date", sort=True).groups.items():
            group_index = pd.Index(positions)
            equity_index = group_index[equity_mask.loc[group_index].to_numpy()]
            if equity_index.empty:
                continue
            target = float(merged.loc[equity_index, "base_weight"].sum())
            raw_total = float(merged.loc[equity_index, "raw_tilted_weight"].sum())
            if raw_total > 0:
                merged.loc[equity_index, "weight"] = (
                    merged.loc[equity_index, "raw_tilted_weight"] / raw_total * target
                )
            else:
                # An extreme lambda could clip every equity name. Preserve the
                # base allocation instead of creating an unfunded portfolio.
                merged.loc[equity_index, "weight"] = merged.loc[
                    equity_index, "base_weight"
                ]

    # lam=0 is deliberately not renormalised, preserving exact row-for-row
    # equality with the source weights. Other variants preserve each date's
    # original equity target and leave crypto unchanged.
    base_sums = merged.groupby("effective_date")["base_weight"].sum()
    tilted_sums = merged.groupby("effective_date")["weight"].sum()
    if not np.allclose(base_sums, tilted_sums, atol=1e-10):
        raise RuntimeError("Sentiment tilt changed the portfolio's invested total")
    if (merged["weight"] < -1e-12).any():
        raise RuntimeError("Sentiment tilt produced a negative final weight")
    used = merged["signal_available"] & merged["sentiment_source_date"].notna()
    if not (
        merged.loc[used, "sentiment_source_date"]
        < merged.loc[used, "effective_date"]
    ).all():
        raise RuntimeError("Sentiment look-ahead invariant failed")

    return merged.sort_values(["effective_date", "ticker"], kind="stable").reset_index(drop=True)


def portfolio_returns_from_weights(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    """Apply a rebalance weight schedule to long-format daily asset returns."""
    required_returns = {"date", "ticker", "daily_return"}
    required_weights = {"effective_date", "ticker", "weight"}
    if not required_returns.issubset(returns.columns):
        raise ValueError(f"returns needs {sorted(required_returns)}")
    if not required_weights.issubset(weights.columns):
        raise ValueError(f"weights needs {sorted(required_weights)}")

    asset_returns = returns[list(required_returns)].copy()
    asset_returns["date"] = (
        pd.to_datetime(asset_returns["date"], utc=True).dt.tz_localize(None).dt.normalize()
    )
    matrix = asset_returns.pivot(index="date", columns="ticker", values="daily_return")
    matrix = matrix.sort_index().sort_index(axis=1).dropna(how="any")
    schedule = weights.pivot(index="effective_date", columns="ticker", values="weight")
    schedule.index = pd.to_datetime(schedule.index)
    schedule = schedule.sort_index().reindex(columns=matrix.columns)
    if schedule.isna().any().any():
        raise ValueError("Weight schedule and return tickers do not match")

    live = matrix.loc[schedule.index.min():]
    daily_weights = schedule.reindex(live.index).ffill()
    if daily_weights.isna().any().any():
        raise RuntimeError("Weight schedule does not cover the full OOS period")
    portfolio_return = (live * daily_weights).sum(axis=1)
    growth = (1.0 + portfolio_return).cumprod()
    drawdown = growth.div(growth.cummax()).sub(1.0)
    return pd.DataFrame(
        {
            "date": portfolio_return.index,
            "daily_return": portfolio_return.to_numpy(),
            "growth_of_1": growth.to_numpy(),
            "drawdown": drawdown.to_numpy(),
        }
    )


def evaluate_fusion_variants(
    base_weights: pd.DataFrame,
    equity_returns: pd.DataFrame,
    sentiment: pd.DataFrame,
    window: int = 60,
    min_periods: int = 20,
) -> dict[str, Any]:
    """Evaluate the fixed base, momentum (+1), and contrarian (-1) variants."""
    variants = {"base": 0.0, "momentum": 1.0, "contrarian": -1.0}
    output: dict[str, Any] = {"weights": {}, "returns": {}}
    metric_rows = []
    for name, lam in variants.items():
        tilted = apply_sentiment(
            base_weights, sentiment, lam, window=window, min_periods=min_periods
        )
        daily = portfolio_returns_from_weights(equity_returns, tilted)
        metrics = performance_metrics(daily["daily_return"], periods_per_year=252)
        output["weights"][name] = tilted
        output["returns"][name] = daily
        metric_rows.append(
            {
                "variant": name,
                "lambda": lam,
                "final_growth_of_1": float(daily["growth_of_1"].iloc[-1]),
                **metrics,
            }
        )
    output["metrics"] = pd.DataFrame(metric_rows)
    return output
