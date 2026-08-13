"""Station 3 portfolio construction and walk-forward OOS backtesting.

The module implements the frozen specification in ``report/OUTLINE.md``:
an expanding estimation window, monthly rebalancing, long-only fully-invested
weights, and weights that become effective on the trading day *after* they are
estimated.  No asset or crypto exposure caps are imposed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize


SUPPORTED_METHODS = (
    "equal_weight",
    "min_variance",
    "max_sharpe",
    "risk_parity",
)


@dataclass(frozen=True)
class BacktestSpec:
    """Resolved assumptions for one asset-family backtest."""

    asset_family: str
    initial_window: int
    periods_per_year: int


def performance_metrics(
    daily_returns: pd.Series, periods_per_year: int = 252
) -> dict[str, float]:
    """Calculate the four fact-sheet metrics required by the Part B brief.

    Annualised return is the geometric compound return at the requested
    frequency. Annualised volatility is sample standard deviation multiplied
    by ``sqrt(periods_per_year)``. Sharpe uses a stated zero risk-free rate and
    arithmetic annualisation. Maximum drawdown is the worst percentage fall
    from the running peak of growth of one dollar.

    Parameters
    ----------
    daily_returns
        One-dimensional OOS simple-return series.
    periods_per_year
        252 for equity/combined funds and 365 for crypto-only funds.
    """
    returns = pd.Series(daily_returns, dtype="float64").dropna()
    if returns.empty:
        return {
            "annualised_return": np.nan,
            "annualised_volatility": np.nan,
            "sharpe": np.nan,
            "max_drawdown": np.nan,
        }
    if (returns <= -1).any():
        raise ValueError("daily_returns contains a return <= -100%")

    growth = (1.0 + returns).cumprod()
    years = len(returns) / float(periods_per_year)
    annualised_return = float(growth.iloc[-1] ** (1.0 / years) - 1.0)
    annualised_volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year))
    sharpe = (
        float(returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year))
        if returns.std(ddof=1) > 0
        else np.nan
    )
    drawdown = growth.div(growth.cummax()).sub(1.0)
    return {
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
    }


def _normalise_method(method: str) -> str:
    aliases = {
        "equal": "equal_weight",
        "equal-weight": "equal_weight",
        "minimum_variance": "min_variance",
        "minimum-variance": "min_variance",
        "maximum_sharpe": "max_sharpe",
        "maximum-sharpe": "max_sharpe",
        "tangency": "max_sharpe",
        "risk-parity": "risk_parity",
    }
    resolved = aliases.get(str(method).strip().lower(), str(method).strip().lower())
    if resolved not in SUPPORTED_METHODS:
        raise ValueError(
            f"Unknown method {method!r}; choose one of {SUPPORTED_METHODS}"
        )
    return resolved


def _prepare_returns(
    returns: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, BacktestSpec]:
    """Convert supported long/wide inputs to a complete date-by-ticker matrix."""
    if not isinstance(returns, pd.DataFrame) or returns.empty:
        raise ValueError("returns must be a non-empty pandas DataFrame")

    frame = returns.copy()
    if {"date", "ticker", "daily_return"}.issubset(frame.columns):
        frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.tz_localize(None)
        if frame.duplicated(["date", "ticker"]).any():
            raise ValueError("returns contains duplicate date-ticker observations")

        asset_classes = (
            set(frame["asset_class"].dropna().astype(str).str.lower())
            if "asset_class" in frame.columns
            else set()
        )
        if asset_classes == {"equity"}:
            asset_family = "equity"
        elif asset_classes == {"crypto"}:
            asset_family = "crypto"
        elif asset_classes == {"equity", "crypto"}:
            asset_family = "combined"
        else:
            asset_family = str(frame.attrs.get("asset_family", "")).lower()
            if asset_family not in {"equity", "crypto", "combined"}:
                raise ValueError(
                    "Long-format returns needs asset_class values that identify "
                    "equity, crypto, or both"
                )

        metadata_columns = [c for c in ("ticker", "asset_class", "sector") if c in frame]
        metadata = frame[metadata_columns].drop_duplicates("ticker").set_index("ticker")
        if "asset_class" not in metadata:
            metadata["asset_class"] = asset_family
        if "sector" not in metadata:
            metadata["sector"] = pd.NA
        matrix = frame.pivot(index="date", columns="ticker", values="daily_return")
    else:
        matrix = frame.copy()
        if "date" in matrix.columns:
            matrix = matrix.set_index("date")
        matrix.index = pd.to_datetime(matrix.index, utc=True).tz_localize(None)
        asset_family = str(frame.attrs.get("asset_family", "")).lower()
        if asset_family not in {"equity", "crypto", "combined"}:
            raise ValueError(
                "Wide returns must set DataFrame.attrs['asset_family'] to "
                "'equity', 'crypto', or 'combined'"
            )
        metadata = pd.DataFrame(index=pd.Index(matrix.columns, name="ticker"))
        metadata["asset_class"] = (
            "crypto" if asset_family == "crypto" else "equity"
        )
        metadata["sector"] = pd.NA

    matrix = matrix.sort_index().sort_index(axis=1).apply(pd.to_numeric, errors="coerce")
    matrix = matrix.loc[~matrix.index.duplicated(keep="first")]
    # A common panel is required by covariance optimisation. Part A's panels
    # are complete apart from each ticker's first undefined return.
    matrix = matrix.dropna(axis=0, how="any")
    if matrix.empty or matrix.shape[1] < 2:
        raise ValueError("returns must contain at least two assets with common dates")

    metadata = metadata.reindex(matrix.columns)
    metadata.index.name = "ticker"
    spec = BacktestSpec(
        asset_family=asset_family,
        initial_window=365 if asset_family == "crypto" else 252,
        periods_per_year=365 if asset_family == "crypto" else 252,
    )
    if len(matrix) <= spec.initial_window:
        raise ValueError(
            f"{asset_family} needs more than {spec.initial_window} common return dates"
        )
    return matrix, metadata, spec


def _normalise_covariance_estimator(estimator: str) -> str:
    """Resolve supported covariance-estimator names without changing defaults."""
    aliases = {
        "sample": "sample",
        "sample_covariance": "sample",
        "ledoit_wolf": "ledoit_wolf",
        "ledoit-wolf": "ledoit_wolf",
        "lw": "ledoit_wolf",
    }
    resolved = aliases.get(str(estimator).strip().lower())
    if resolved is None:
        raise ValueError("covariance_estimator must be 'sample' or 'ledoit_wolf'")
    return resolved


def _regularised_covariance(
    history: pd.DataFrame,
    periods_per_year: int,
    estimator: str = "sample",
) -> np.ndarray:
    """Estimate annualised covariance and add a scale-proportional numeric ridge.

    ``sample`` is the frozen baseline. ``ledoit_wolf`` is an untuned robustness
    extension: its shrinkage intensity is estimated from each expanding window,
    never selected using OOS performance.
    """
    resolved = _normalise_covariance_estimator(estimator)
    if resolved == "sample":
        covariance = history.cov().to_numpy(dtype="float64") * periods_per_year
    else:
        try:
            from sklearn.covariance import LedoitWolf
        except ImportError as exc:  # pragma: no cover - dependency guidance
            raise ImportError(
                "Ledoit-Wolf robustness analysis requires scikit-learn from "
                "requirements-dev.txt"
            ) from exc
        covariance = (
            LedoitWolf(assume_centered=False)
            .fit(history.to_numpy(dtype="float64"))
            .covariance_
            * periods_per_year
        )
    average_variance = float(np.trace(covariance) / len(covariance))
    ridge = max(average_variance * 1e-8, 1e-12)
    return covariance + np.eye(len(covariance)) * ridge


def _solve_weights(
    history: pd.DataFrame,
    method: str,
    periods_per_year: int,
    previous: np.ndarray | None = None,
    covariance_estimator: str = "sample",
) -> np.ndarray:
    """Solve one long-only, fully-invested portfolio without exposure caps."""
    n_assets = history.shape[1]
    equal = np.full(n_assets, 1.0 / n_assets)
    if method == "equal_weight":
        return equal

    covariance = _regularised_covariance(
        history, periods_per_year, estimator=covariance_estimator
    )
    mean = history.mean().to_numpy(dtype="float64") * periods_per_year
    start = previous if previous is not None else equal
    start = np.clip(np.asarray(start, dtype="float64"), 0.0, None)
    start = start / start.sum() if start.sum() > 0 else equal
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = [(0.0, 1.0)] * n_assets

    if method == "min_variance":
        result = minimize(
            fun=lambda w: float(w @ covariance @ w),
            x0=start,
            jac=lambda w: 2.0 * covariance @ w,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 1_000},
        )
    elif method == "max_sharpe":
        def negative_sharpe(w: np.ndarray) -> float:
            variance = max(float(w @ covariance @ w), 1e-18)
            return -float(w @ mean) / np.sqrt(variance)

        def negative_sharpe_jac(w: np.ndarray) -> np.ndarray:
            cov_w = covariance @ w
            variance = max(float(w @ cov_w), 1e-18)
            numerator = float(w @ mean)
            gradient = mean / np.sqrt(variance) - numerator * cov_w / variance ** 1.5
            return -gradient

        result = minimize(
            fun=negative_sharpe,
            x0=start,
            jac=negative_sharpe_jac,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 2_000},
        )
    else:  # risk_parity
        # Convex risk-budgeting formulation: minimise
        # 0.5*x'Sigma*x - sum_i b_i log(x_i), then normalise x. Its KKT
        # conditions imply equal risk contributions. L-BFGS-B is much more
        # stable than directly minimising tiny daily covariance contributions.
        budget = np.full(n_assets, 1.0 / n_assets)
        # The auxiliary risk-budgeting variable x is not a portfolio weight
        # until after optimisation, so it must not be normalised at the start.
        # sqrt(b_i / variance_i) is on the natural scale of the KKT equation
        # x_i * (Sigma x)_i = b_i and avoids line-search failure near the log
        # barrier that a tiny sum-to-one starting vector can cause.
        x0 = np.sqrt(budget / np.diag(covariance))

        def rb_objective(x: np.ndarray) -> float:
            return float(0.5 * x @ covariance @ x - budget @ np.log(x))

        def rb_gradient(x: np.ndarray) -> np.ndarray:
            return covariance @ x - budget / x

        result = minimize(
            fun=rb_objective,
            x0=x0,
            jac=rb_gradient,
            method="L-BFGS-B",
            bounds=[(1e-10, None)] * n_assets,
            options={
                "ftol": 1e-12,
                "gtol": 1e-8,
                "maxiter": 2_000,
                "maxls": 100,
            },
        )

    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"{method} optimisation failed: {result.message}")
    weights = np.clip(result.x, 0.0, None)
    if weights.sum() <= 0:
        raise RuntimeError(f"{method} optimisation returned zero total weight")
    weights /= weights.sum()
    return weights


def _monthly_rebalance_dates(matrix: pd.DataFrame, initial_window: int) -> list[pd.Timestamp]:
    # Determine each month's first trading date from the *full* calendar, then
    # filter by estimation-window eligibility. Grouping only the eligible tail
    # would incorrectly label a late-month window-end date (for example
    # 2020-12-31) as that month's "first" trading day.
    calendar = matrix.index
    first_per_month = (
        pd.Series(calendar, index=calendar)
        .groupby(calendar.to_period("M"), sort=True)
        .first()
        .tolist()
    )
    first_per_month = [
        date for date in first_per_month
        if matrix.index.get_loc(date) >= initial_window - 1
    ]
    # A rebalance on the final observation has no next trading day on which
    # its weights could become effective, so it is not a usable decision.
    return [date for date in first_per_month if matrix.index.get_loc(date) + 1 < len(matrix)]


def simulate_rebalanced_portfolio(
    asset_returns: pd.DataFrame,
    target_weights: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """Apply a target-weight schedule while allowing holdings to drift daily.

    Parameters
    ----------
    asset_returns
        Complete date-by-ticker simple-return matrix.
    target_weights
        Date-by-ticker target weights indexed by the dates on which trades are
        effective.

    Returns
    -------
    tuple
        Daily portfolio returns, pre-trade weights observed on each rebalance
        date, and one-way turnover ``0.5 * sum(abs(target - pre_trade))``.

    Notes
    -----
    A target is applied at the start of its effective date. Between those
    dates, end-of-day holdings drift with each asset's realised return. Initial
    funding is assigned zero turnover because it is not a rebalance from an
    existing portfolio.
    """
    matrix = asset_returns.copy().sort_index().sort_index(axis=1)
    schedule = target_weights.copy().sort_index().reindex(columns=matrix.columns)
    if matrix.empty or schedule.empty:
        raise ValueError("asset_returns and target_weights must be non-empty")
    if matrix.index.has_duplicates or schedule.index.has_duplicates:
        raise ValueError("return and target-weight dates must be unique")
    if schedule.isna().any().any():
        raise ValueError("target_weights and asset_returns tickers do not match")
    if (schedule < -1e-12).any().any():
        raise ValueError("target_weights must be long-only")
    if not np.allclose(schedule.sum(axis=1).to_numpy(), 1.0, atol=1e-8):
        raise ValueError("target_weights must sum to one on every rebalance date")

    live = matrix.loc[schedule.index.min():]
    if live.empty or not schedule.index.isin(live.index).all():
        raise ValueError("Every target-weight date must exist in asset_returns")
    if live.isna().any().any():
        raise ValueError("asset_returns must be complete during the live period")

    current_end_weights: pd.Series | None = None
    portfolio_returns: list[float] = []
    return_dates: list[pd.Timestamp] = []
    pre_trade_rows: list[pd.Series] = []
    turnover_values: list[float] = []

    for date, realised in live.iterrows():
        if date in schedule.index:
            target = schedule.loc[date].astype("float64")
            if current_end_weights is None:
                # Initial funding is not counted as a post-launch trade.
                pre_trade = target.copy()
                turnover = 0.0
            else:
                pre_trade = current_end_weights.copy()
                turnover = 0.5 * float((target - pre_trade).abs().sum())
            pre_trade.name = date
            pre_trade_rows.append(pre_trade)
            turnover_values.append(turnover)
            start_weights = target
        else:
            if current_end_weights is None:
                raise RuntimeError("No target weights are live on the first OOS date")
            start_weights = current_end_weights

        realised = realised.astype("float64")
        daily_return = float(start_weights @ realised)
        gross_value = 1.0 + daily_return
        if not np.isfinite(gross_value) or gross_value <= 0:
            raise RuntimeError("Portfolio value became non-positive during weight drift")
        current_end_weights = start_weights.mul(1.0 + realised).div(gross_value)
        if not np.isfinite(current_end_weights.to_numpy()).all():
            raise RuntimeError("Weight drift produced non-finite holdings")
        current_end_weights = current_end_weights / current_end_weights.sum()
        return_dates.append(date)
        portfolio_returns.append(daily_return)

    pre_trade_weights = pd.DataFrame(pre_trade_rows).reindex(
        index=schedule.index, columns=schedule.columns
    )
    turnover = pd.Series(turnover_values, index=schedule.index, name="turnover")
    returns = pd.Series(
        portfolio_returns, index=pd.DatetimeIndex(return_dates), name="daily_return"
    )
    return returns, pre_trade_weights, turnover


def oos_backtest(
    returns: pd.DataFrame,
    method: str = "min_variance",
    covariance_estimator: str = "sample",
) -> dict[str, Any]:
    """Run a monthly expanding-window walk-forward out-of-sample backtest.

    Parameters
    ----------
    returns
        Preferably a long frame with ``date``, ``ticker``, ``daily_return``
        and ``asset_class``. A wide date-by-ticker matrix is also accepted if
        ``returns.attrs['asset_family']`` is set.
    method
        One of equal weight, minimum variance, maximum Sharpe/tangency, or
        risk parity (see ``SUPPORTED_METHODS``).
    covariance_estimator
        ``sample`` preserves the frozen baseline. ``ledoit_wolf`` enables the
        separately reported, untuned covariance-shrinkage robustness study.

    Returns
    -------
    dict
        ``daily_returns`` contains OOS return, growth and drawdown by date;
        ``weights`` contains each rebalance/effective date and ticker weight;
        ``audit`` records the estimation start/end and number of observations;
        ``metrics`` contains the required fact-sheet statistics plus turnover;
        and ``spec`` records the resolved family/window/annualisation settings.

    Notes
    -----
    Each first-trading-day-of-month rebalance includes that date's close-to-
    close return in the expanding history. The resulting weight is first used
    on the *next* trading date. Therefore ``estimation_end < effective_date``
    and every realised OOS return is strictly later than the data used to form
    its applicable weight.
    """
    resolved_method = _normalise_method(method)
    resolved_covariance = _normalise_covariance_estimator(covariance_estimator)
    matrix, metadata, spec = _prepare_returns(returns)
    rebalance_dates = _monthly_rebalance_dates(matrix, spec.initial_window)
    if not rebalance_dates:
        raise ValueError("No usable monthly rebalance date after the initial window")

    schedules: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    previous: np.ndarray | None = None

    for rebalance_date in rebalance_dates:
        history = matrix.loc[:rebalance_date]
        effective_position = matrix.index.get_loc(rebalance_date) + 1
        effective_date = matrix.index[effective_position]
        weights = _solve_weights(
            history,
            resolved_method,
            spec.periods_per_year,
            previous=previous,
            covariance_estimator=resolved_covariance,
        )
        previous = weights
        schedules.append({"effective_date": effective_date, "weights": weights})
        audit_rows.append(
            {
                "rebalance_date": rebalance_date,
                "effective_date": effective_date,
                "estimation_start": history.index.min(),
                "estimation_end": history.index.max(),
                "n_estimation_observations": len(history),
            }
        )
    weight_schedule = pd.DataFrame(
        [dict(effective_date=s["effective_date"], **dict(zip(matrix.columns, s["weights"])))
         for s in schedules]
    ).set_index("effective_date")
    portfolio_return, pre_trade_schedule, turnover_series = (
        simulate_rebalanced_portfolio(matrix, weight_schedule)
    )

    weight_rows: list[dict[str, Any]] = []
    audit_by_effective = {row["effective_date"]: row for row in audit_rows}
    for effective_date, target in weight_schedule.iterrows():
        pre_trade = pre_trade_schedule.loc[effective_date]
        turnover = float(turnover_series.loc[effective_date])
        audit_by_effective[effective_date]["turnover"] = turnover
        for ticker in matrix.columns:
            meta = metadata.loc[ticker]
            weight_rows.append(
                {
                    "rebalance_date": audit_by_effective[effective_date]["rebalance_date"],
                    "effective_date": effective_date,
                    "estimation_end": audit_by_effective[effective_date]["estimation_end"],
                    "ticker": ticker,
                    "asset_class": meta.get("asset_class", pd.NA),
                    "sector": meta.get("sector", pd.NA),
                    "pre_trade_weight": float(pre_trade.loc[ticker]),
                    "weight": float(target.loc[ticker]),
                    "trade_weight_change": float(target.loc[ticker] - pre_trade.loc[ticker]),
                    "rebalance_turnover": turnover,
                }
            )
    growth = (1.0 + portfolio_return).cumprod()
    drawdown = growth.div(growth.cummax()).sub(1.0)
    daily_output = pd.DataFrame(
        {
            "date": portfolio_return.index,
            "daily_return": portfolio_return.to_numpy(),
            "growth_of_1": growth.to_numpy(),
            "drawdown": drawdown.to_numpy(),
        }
    )

    weights_output = pd.DataFrame(weight_rows)
    audit_output = pd.DataFrame(audit_rows)
    metrics = performance_metrics(portfolio_return, spec.periods_per_year)
    post_launch_turnover = turnover_series.iloc[1:]
    metrics["turnover"] = (
        float(post_launch_turnover.mean()) if not post_launch_turnover.empty else 0.0
    )

    # Invariants are checked here so a bad optimiser cannot silently feed the
    # report or app. Detailed cross-method checks live in test_no_lookahead.py.
    weight_sums = weights_output.groupby("effective_date")["weight"].sum()
    if not np.allclose(weight_sums.to_numpy(), 1.0, atol=1e-8):
        raise RuntimeError("Portfolio weights do not sum to one")
    if (weights_output["weight"] < -1e-12).any():
        raise RuntimeError("Portfolio contains a negative weight")
    pre_trade_sums = weights_output.groupby("effective_date")["pre_trade_weight"].sum()
    if not np.allclose(pre_trade_sums.to_numpy(), 1.0, atol=1e-8):
        raise RuntimeError("Pre-trade portfolio weights do not sum to one")
    if not (audit_output["estimation_end"] < audit_output["effective_date"]).all():
        raise RuntimeError("Look-ahead invariant failed: estimation_end >= effective_date")

    return {
        "daily_returns": daily_output,
        "weights": weights_output,
        "audit": audit_output,
        "metrics": metrics,
        "spec": {
            "asset_family": spec.asset_family,
            "method": resolved_method,
            "initial_window": spec.initial_window,
            "periods_per_year": spec.periods_per_year,
            "rebalance_frequency": "monthly_first_trading_day",
            "risk_free_rate": 0.0,
            "transaction_cost": 0.0,
            "covariance_estimator": resolved_covariance,
        },
    }
