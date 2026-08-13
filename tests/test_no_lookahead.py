"""Verification tests for the Part B walk-forward portfolio engine.

Run from the project root with:

    python tests/test_no_lookahead.py
"""
from __future__ import annotations

import pathlib
import sys
import argparse

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.portfolios import SUPPORTED_METHODS, oos_backtest  # noqa: E402


def _synthetic_long_panel() -> pd.DataFrame:
    rng = np.random.default_rng(5545)
    dates = pd.bdate_range("2019-01-01", periods=520)
    tickers = ["LOW_VOL", "TREND", "CYCLICAL", "DEFENSIVE"]
    means = np.array([0.00015, 0.00075, 0.00035, 0.00020])
    vols = np.array([0.004, 0.018, 0.028, 0.009])
    common = rng.normal(0.0, 0.006, size=(len(dates), 1))
    idiosyncratic = rng.normal(size=(len(dates), len(tickers))) * vols
    values = means + 0.35 * common + idiosyncratic
    wide = pd.DataFrame(values, index=dates, columns=tickers)
    wide.columns.name = "ticker"
    long = wide.rename_axis("date").stack().rename("daily_return").reset_index()
    long["asset_class"] = "equity"
    long["sector"] = long["ticker"]
    return long


def test_no_lookahead() -> None:
    panel = _synthetic_long_panel()
    for method in SUPPORTED_METHODS:
        result = oos_backtest(panel, method)
        audit = result["audit"]
        assert (audit["estimation_end"] < audit["effective_date"]).all()
        assert result["daily_returns"]["date"].min() == audit["effective_date"].min()
        sums = result["weights"].groupby("effective_date")["weight"].sum()
        assert np.allclose(sums, 1.0, atol=1e-8)
        assert (result["weights"]["weight"] >= -1e-12).all()


def test_methods_produce_distinct_weights() -> None:
    panel = _synthetic_long_panel()
    matrices = {}
    for method in SUPPORTED_METHODS:
        result = oos_backtest(panel, method)
        matrices[method] = result["weights"].pivot(
            index="effective_date", columns="ticker", values="weight"
        )
    for index, left_method in enumerate(SUPPORTED_METHODS):
        for right_method in SUPPORTED_METHODS[index + 1:]:
            left, right = matrices[left_method].align(matrices[right_method])
            assert not np.allclose(left, right, atol=1e-6), (
                f"{left_method} and {right_method} produced equal weights"
            )


def verify_real_data() -> None:
    """Run all 12 required funds and print the Prompt-2 audit evidence."""
    from src.calendar_merge import combine_equity_crypto_returns
    from src.etl import load_clean_crypto, load_clean_equities
    from src.features import daily_returns

    equities, _, _, _ = load_clean_equities()
    crypto, _, _, _ = load_clean_crypto()
    sector_map = equities[["ticker", "sector"]].drop_duplicates("ticker")

    equity_returns = daily_returns(equities).merge(sector_map, on="ticker", how="left")
    equity_returns["asset_class"] = "equity"
    crypto_returns = daily_returns(crypto)
    crypto_returns["asset_class"] = "crypto"
    crypto_returns["sector"] = pd.NA
    combined_returns = combine_equity_crypto_returns(equities, crypto)
    families = {
        "equity": equity_returns,
        "crypto": crypto_returns,
        "combined": combined_returns,
    }

    print("family,method,first_oos,last_oos,rebalances,max_weight_sum_error,min_weight")
    for family, panel in families.items():
        matrices = {}
        for method in SUPPORTED_METHODS:
            result = oos_backtest(panel, method)
            audit = result["audit"]
            assert (audit["estimation_end"] < audit["effective_date"]).all()
            weights = result["weights"]
            sums = weights.groupby("effective_date")["weight"].sum()
            max_sum_error = float((sums - 1.0).abs().max())
            matrices[method] = weights.pivot(
                index="effective_date", columns="ticker", values="weight"
            )
            daily = result["daily_returns"]
            print(
                f"{family},{method},{daily['date'].min().date()},"
                f"{daily['date'].max().date()},{len(audit)},"
                f"{max_sum_error:.3e},{weights['weight'].min():.3e}"
            )

        for index, left_method in enumerate(SUPPORTED_METHODS):
            for right_method in SUPPORTED_METHODS[index + 1:]:
                left, right = matrices[left_method].align(matrices[right_method])
                max_difference = float(np.max(np.abs(left.to_numpy() - right.to_numpy())))
                assert max_difference > 1e-6, (
                    f"{family}: {left_method} and {right_method} weights are equal"
                )
                print(
                    f"WEIGHT_DIFFERENCE,{family},{left_method},{right_method},"
                    f"max_abs_diff={max_difference:.6f}"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real", action="store_true", help="also verify all 12 funds on hosted data"
    )
    args = parser.parse_args()
    test_no_lookahead()
    print("no-look-ahead and weight invariants: PASS")
    test_methods_produce_distinct_weights()
    print("cross-method weight differentiation: PASS")
    if args.real:
        verify_real_data()
        print("real-data 12-fund acceptance checks: PASS")
