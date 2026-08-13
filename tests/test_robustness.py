"""Tests for the pre-specified robustness extensions."""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.portfolios import oos_backtest, simulate_rebalanced_portfolio  # noqa: E402
from src.robustness import (  # noqa: E402
    evaluate_covariance_shrinkage,
    transaction_cost_sensitivity,
)


def _panel(family: str = "equity") -> pd.DataFrame:
    periods = 520 if family == "equity" else 730
    dates = pd.bdate_range("2020-01-01", periods=periods) if family == "equity" else pd.date_range("2020-01-01", periods=periods)
    rng = np.random.default_rng(5545)
    rows = []
    common = rng.normal(0.0003, 0.008 if family == "equity" else 0.025, len(dates))
    for index, ticker in enumerate(("A", "B", "C", "D")):
        returns = common * (0.5 + index * 0.15) + rng.normal(0.0001, 0.004 + index * 0.002, len(dates))
        rows.extend(
            {
                "date": date,
                "ticker": ticker,
                "daily_return": value,
                "asset_class": family,
                "sector": "Test" if family == "equity" else pd.NA,
            }
            for date, value in zip(dates, returns)
        )
    return pd.DataFrame(rows)


def test_ledoit_wolf_is_separate_and_lookahead_safe() -> None:
    panel = _panel("equity")
    baseline = oos_backtest(panel, "min_variance")
    explicit = oos_backtest(panel, "min_variance", covariance_estimator="sample")
    assert np.array_equal(
        baseline["weights"]["weight"].to_numpy(),
        explicit["weights"]["weight"].to_numpy(),
    )

    study = evaluate_covariance_shrinkage(
        {"equity": panel}, {"equity_min_variance": baseline}, methods=("min_variance",)
    )
    comparison = study["comparison"]
    assert set(comparison["covariance_estimator"]) == {"sample", "ledoit_wolf"}
    assert len(comparison) == 2
    assert comparison["n_rebalances"].nunique() == 1
    assert comparison["first_oos_date"].nunique() == 1


def test_transaction_costs_are_deterministic_and_reduce_growth() -> None:
    baseline = oos_backtest(_panel("equity"), "risk_parity")
    sensitivity = transaction_cost_sensitivity(
        {"equity_risk_parity": baseline}, cost_levels_bps=(0, 10, 100)
    )
    assert sensitivity["cost_bps"].tolist() == [0, 10, 100]
    assert sensitivity["final_growth_of_1"].is_monotonic_decreasing
    assert sensitivity.loc[sensitivity["cost_bps"].eq(0), "growth_drag_vs_gross"].iat[0] == 0
    assert sensitivity.loc[sensitivity["cost_bps"].eq(100), "growth_drag_vs_gross"].iat[0] < 0


def test_holdings_drift_and_pre_trade_turnover_are_exact() -> None:
    dates = pd.bdate_range("2023-01-02", periods=4)
    returns = pd.DataFrame(
        {"A": [0.10, 0.00, 0.00, 0.00], "B": [0.00, 0.00, 0.00, 0.00]},
        index=dates,
    )
    targets = pd.DataFrame(
        {"A": [0.5, 0.5], "B": [0.5, 0.5]}, index=dates[[0, 2]]
    )
    portfolio, pre_trade, turnover = simulate_rebalanced_portfolio(returns, targets)
    assert np.isclose(portfolio.iloc[0], 0.05)
    assert np.isclose(pre_trade.loc[dates[2], "A"], 1.1 / 2.1)
    expected = 0.5 * (abs(0.5 - 1.1 / 2.1) + abs(0.5 - 1.0 / 2.1))
    assert np.isclose(turnover.loc[dates[2]], expected)


def test_equal_weight_turnover_includes_drift() -> None:
    baseline = oos_backtest(_panel("equity"), "equal_weight")
    turnover = baseline["audit"]["turnover"].iloc[1:]
    assert turnover.gt(0).any()
    assert np.isclose(baseline["metrics"]["turnover"], turnover.mean())


if __name__ == "__main__":
    test_ledoit_wolf_is_separate_and_lookahead_safe()
    test_transaction_costs_are_deterministic_and_reduce_growth()
    test_holdings_drift_and_pre_trade_turnover_are_exact()
    test_equal_weight_turnover_includes_drift()
    print("covariance shrinkage and transaction-cost robustness: PASS")
