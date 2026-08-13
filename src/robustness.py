"""Pre-specified robustness extensions for the Part B fund evidence.

The frozen 12-fund baseline remains untouched. This module evaluates two
additional questions: whether automatically estimated Ledoit-Wolf covariance
shrinkage changes covariance-sensitive funds, and how realised results degrade
under fixed transaction-cost assumptions.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.portfolios import oos_backtest, performance_metrics


SHRINKAGE_METHODS = ("min_variance", "max_sharpe")
TRANSACTION_COST_LEVELS_BPS = (0, 10, 25, 50, 100)


def evaluate_covariance_shrinkage(
    family_panels: Mapping[str, pd.DataFrame],
    baseline_results: Mapping[str, Mapping[str, Any]],
    methods: Iterable[str] = SHRINKAGE_METHODS,
) -> dict[str, pd.DataFrame]:
    """Compare sample covariance with untuned Ledoit-Wolf OOS results.

    Ledoit-Wolf estimates its shrinkage intensity separately inside every
    expanding estimation window. No OOS result is used to choose a parameter.
    The supplied baseline results are reused so the canonical 12 funds are not
    silently recomputed or replaced.
    """
    metric_rows: list[dict[str, Any]] = []
    return_frames: list[pd.DataFrame] = []

    for family, panel in family_panels.items():
        for method in methods:
            fund_id = f"{family}_{method}"
            if fund_id not in baseline_results:
                raise KeyError(f"Missing baseline result {fund_id}")
            variants = {
                "sample": baseline_results[fund_id],
                "ledoit_wolf": oos_backtest(
                    panel, method, covariance_estimator="ledoit_wolf"
                ),
            }
            for estimator, result in variants.items():
                audit = result["audit"]
                if not (audit["estimation_end"] < audit["effective_date"]).all():
                    raise RuntimeError("Shrinkage robustness backtest found look-ahead")
                daily = result["daily_returns"].copy()
                daily.insert(1, "asset_family", family)
                daily.insert(2, "method", method)
                daily.insert(3, "covariance_estimator", estimator)
                return_frames.append(daily)
                metric_rows.append(
                    {
                        "asset_family": family,
                        "method": method,
                        "covariance_estimator": estimator,
                        **result["metrics"],
                        "first_oos_date": daily["date"].min(),
                        "last_oos_date": daily["date"].max(),
                        "n_oos_days": len(daily),
                        "n_rebalances": len(audit),
                    }
                )

    comparison = pd.DataFrame(metric_rows).sort_values(
        ["asset_family", "method", "covariance_estimator"], kind="stable"
    )
    baseline = comparison.loc[
        comparison["covariance_estimator"].eq("sample"),
        [
            "asset_family", "method", "annualised_return",
            "annualised_volatility", "sharpe", "max_drawdown",
        ],
    ].rename(
        columns={
            "annualised_return": "baseline_annualised_return",
            "annualised_volatility": "baseline_annualised_volatility",
            "sharpe": "baseline_sharpe",
            "max_drawdown": "baseline_max_drawdown",
        }
    )
    comparison = comparison.merge(
        baseline, on=["asset_family", "method"], how="left", validate="many_to_one"
    )
    comparison["delta_annualised_return"] = (
        comparison["annualised_return"] - comparison["baseline_annualised_return"]
    )
    comparison["delta_annualised_volatility"] = (
        comparison["annualised_volatility"]
        - comparison["baseline_annualised_volatility"]
    )
    comparison["delta_sharpe"] = comparison["sharpe"] - comparison["baseline_sharpe"]
    comparison["delta_max_drawdown"] = (
        comparison["max_drawdown"] - comparison["baseline_max_drawdown"]
    )
    returns = pd.concat(return_frames, ignore_index=True).sort_values(
        ["date", "asset_family", "method", "covariance_estimator"], kind="stable"
    )
    return {"comparison": comparison.reset_index(drop=True), "returns": returns}


def _rebalance_turnover(weights: pd.DataFrame) -> pd.Series:
    required = {"effective_date", "ticker", "weight"}
    missing = required - set(weights.columns)
    if missing:
        raise ValueError(f"weights missing required columns: {sorted(missing)}")
    frame = weights.copy()
    frame["effective_date"] = pd.to_datetime(frame["effective_date"])
    matrix = frame.pivot(index="effective_date", columns="ticker", values="weight")
    matrix = matrix.sort_index().fillna(0.0)
    turnover = matrix.diff().abs().sum(axis=1).mul(0.5)
    # The sensitivity measures rebalancing costs after launch; initial funding
    # from cash is not treated as a strategy turnover event.
    turnover.iloc[0] = 0.0
    return turnover


def transaction_cost_sensitivity(
    fund_results: Mapping[str, Mapping[str, Any]],
    cost_levels_bps: Iterable[int] = TRANSACTION_COST_LEVELS_BPS,
) -> pd.DataFrame:
    """Apply fixed one-way trading costs to each fund's realised OOS returns.

    Cost on an effective rebalance date is ``turnover * bps / 10,000``. The
    experiment is deterministic, reports every pre-specified cost level, and
    never feeds net results back into portfolio formation.
    """
    levels = tuple(int(level) for level in cost_levels_bps)
    if not levels or any(level < 0 for level in levels):
        raise ValueError("cost_levels_bps must contain non-negative integers")

    rows: list[dict[str, Any]] = []
    for fund_id, result in fund_results.items():
        daily = result["daily_returns"][["date", "daily_return"]].copy()
        daily["date"] = pd.to_datetime(daily["date"])
        daily = daily.sort_values("date", kind="stable").set_index("date")
        turnover = _rebalance_turnover(result["weights"])
        aligned_turnover = turnover.reindex(daily.index, fill_value=0.0)
        spec = result["spec"]
        ppy = int(spec["periods_per_year"])
        gross_growth = float((1.0 + daily["daily_return"]).prod())

        for cost_bps in levels:
            cost_rate = aligned_turnover * (cost_bps / 10_000.0)
            net_return = daily["daily_return"] - cost_rate
            metrics = performance_metrics(net_return, ppy)
            net_growth = float((1.0 + net_return).prod())
            rows.append(
                {
                    "fund_id": fund_id,
                    "asset_family": spec["asset_family"],
                    "method": spec["method"],
                    "cost_bps": cost_bps,
                    **metrics,
                    "final_growth_of_1": net_growth,
                    "growth_drag_vs_gross": net_growth - gross_growth,
                    "mean_rebalance_turnover": float(turnover.iloc[1:].mean()),
                    "total_rebalance_turnover": float(turnover.iloc[1:].sum()),
                    "n_cost_events": int(turnover.iloc[1:].gt(0).sum()),
                }
            )

    output = pd.DataFrame(rows).sort_values(
        ["asset_family", "method", "cost_bps"], kind="stable"
    ).reset_index(drop=True)
    zero = output.loc[output["cost_bps"].eq(0)].set_index("fund_id")["sharpe"]
    output["sharpe_change_vs_gross"] = output["sharpe"] - output["fund_id"].map(zero)
    if not np.isfinite(output.select_dtypes(include="number").to_numpy()).all():
        raise RuntimeError("Transaction-cost sensitivity produced non-finite values")
    return output
