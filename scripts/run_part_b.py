"""Single reproducible entry point for every Part B result.

Run from the project root:

    python scripts/run_part_b.py

The deployed Streamlit app never imports this module; it only reads the
precomputed CSV artifacts written here.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import data_access  # noqa: E402
from src.calendar_merge import (  # noqa: E402
    combine_equity_crypto_returns,
    dedupe_news_headlines,
    map_headline_to_trading_day,
)
from src.etl import load_clean_crypto, load_clean_equities  # noqa: E402
from src.features import assemble_headline_panel, daily_returns  # noqa: E402
from src.fusion import evaluate_fusion_variants  # noqa: E402
from src.plot_style import (  # noqa: E402
    ACCENT,
    ACCENT_ALT,
    ACCENT_LINE,
    apply_style,
    asset_class_color,
    sector_color,
)
from src.portfolios import SUPPORTED_METHODS, oos_backtest  # noqa: E402
from src.sentiment import compare_vader_models, ensure_vader_lexicon  # noqa: E402


DATA_DIR = ROOT / "results" / "data"
TABLE_DIR = ROOT / "results" / "tables"
FIGURE_DIR = ROOT / "results" / "figures"

FAMILY_LABELS = {
    "equity": "Equity-only",
    "crypto": "Crypto-only",
    "combined": "Combined",
}
METHOD_LABELS = {
    "equal_weight": "Equal Weight",
    "min_variance": "Minimum Variance",
    "max_sharpe": "Maximum Sharpe",
    "risk_parity": "Risk Parity",
}
METHOD_COLORS = {
    "equal_weight": "#332288",
    "min_variance": "#117733",
    "max_sharpe": "#CC6677",
    "risk_parity": "#88CCEE",
}
FUSION_COLORS = {
    "base": ACCENT,
    "momentum": ACCENT_ALT,
    "contrarian": ACCENT_LINE,
}


def _prepare_foundation() -> dict[str, Any]:
    equities, equity_missing, equity_dupes, equity_outliers = load_clean_equities()
    crypto, crypto_2024, crypto_dupes, crypto_outliers = load_clean_crypto()

    sector_map = equities[["ticker", "sector"]].drop_duplicates("ticker")
    equity_returns = daily_returns(equities).merge(
        sector_map, on="ticker", how="left", validate="many_to_one"
    )
    equity_returns["asset_class"] = "equity"
    crypto_returns = daily_returns(crypto)
    crypto_returns["asset_class"] = "crypto"
    crypto_returns["sector"] = pd.NA
    combined_returns = combine_equity_crypto_returns(equities, crypto)

    news, news_dupes = dedupe_news_headlines(data_access.load_news_headlines())
    equity_calendar = pd.DatetimeIndex(equities["date"].unique()).sort_values()
    news_mapped, news_after_calendar = map_headline_to_trading_day(news, equity_calendar)
    headline_panel = assemble_headline_panel(news_mapped)

    return {
        "equities": equities,
        "crypto": crypto,
        "equity_returns": equity_returns,
        "crypto_returns": crypto_returns,
        "combined_returns": combined_returns,
        "equity_calendar": equity_calendar,
        "headline_panel": headline_panel,
        "foundation_audit": {
            "equity_missing_dates": int(equity_missing["missing_dates_count"].sum()),
            "equity_duplicates": equity_dupes,
            "equity_outliers": len(equity_outliers),
            "crypto_2024_rows": crypto_2024,
            "crypto_duplicates": crypto_dupes,
            "crypto_outliers": len(crypto_outliers),
            "news_duplicates": news_dupes,
            "news_after_calendar": news_after_calendar,
            "headline_panel_rows": len(headline_panel),
        },
    }


def _run_funds(state: dict[str, Any]) -> dict[str, Any]:
    families = {
        "equity": state["equity_returns"],
        "crypto": state["crypto_returns"],
        "combined": state["combined_returns"],
    }
    fund_results: dict[str, dict[str, Any]] = {}
    returns_frames, weight_frames, audit_frames, metric_rows = [], [], [], []

    for family, panel in families.items():
        for method in SUPPORTED_METHODS:
            fund_id = f"{family}_{method}"
            result = oos_backtest(panel, method)
            fund_results[fund_id] = result

            daily = result["daily_returns"].copy()
            daily.insert(1, "fund_id", fund_id)
            daily.insert(2, "asset_family", family)
            daily.insert(3, "method", method)
            returns_frames.append(daily)

            weights = result["weights"].copy()
            weights.insert(2, "fund_id", fund_id)
            # Exact app/marker columns first; estimation_end remains as an
            # additional audit field.
            weights = weights[
                [
                    "rebalance_date", "effective_date", "fund_id", "ticker",
                    "asset_class", "sector", "weight", "estimation_end",
                ]
            ]
            weight_frames.append(weights)

            audit = result["audit"].copy()
            audit.insert(0, "fund_id", fund_id)
            audit.insert(1, "asset_family", family)
            audit.insert(2, "method", method)
            audit_frames.append(audit)

            metric_rows.append(
                {
                    "fund_id": fund_id,
                    "asset_family": family,
                    "method": method,
                    **result["metrics"],
                    "first_oos_date": daily["date"].min(),
                    "last_oos_date": daily["date"].max(),
                    "n_oos_days": len(daily),
                    "n_rebalances": len(result["audit"]),
                }
            )

    fund_returns = pd.concat(returns_frames, ignore_index=True).sort_values(
        ["date", "asset_family", "method"], kind="stable"
    )
    fund_weights = pd.concat(weight_frames, ignore_index=True).sort_values(
        ["effective_date", "fund_id", "ticker"], kind="stable"
    )
    backtest_audit = pd.concat(audit_frames, ignore_index=True).sort_values(
        ["effective_date", "fund_id"], kind="stable"
    )
    metrics = pd.DataFrame(metric_rows).sort_values(
        ["asset_family", "method"], kind="stable"
    ).reset_index(drop=True)

    if metrics["fund_id"].nunique() != 12:
        raise RuntimeError("The required 12-fund matrix was not produced")
    if not (backtest_audit["estimation_end"] < backtest_audit["effective_date"]).all():
        raise RuntimeError("Backtest audit found look-ahead")
    return {
        "fund_results": fund_results,
        "fund_returns": fund_returns,
        "fund_weights": fund_weights,
        "backtest_audit": backtest_audit,
        "metrics": metrics,
    }


def _run_sentiment(state: dict[str, Any]) -> dict[str, Any]:
    # One-time offline build resource. This module is never imported by the app.
    ensure_vader_lexicon(download=True)
    result = compare_vader_models(
        state["headline_panel"],
        trading_calendar=state["equity_calendar"],
        sample_per_sector=5,
        random_state=5545,
    )
    summary = result["summary"].set_index("model")
    if not (
        summary.loc["vader_finance_enhanced", "neutral_rate"]
        < summary.loc["vader_plain", "neutral_rate"]
    ):
        raise RuntimeError("Enhanced VADER did not lower the neutral rate")

    ticker_scores = result["enhanced_ticker_scores"]
    market = (
        ticker_scores.groupby("date", sort=True)
        .agg(
            sentiment=("sentiment", "mean"),
            n_tickers=("ticker", "nunique"),
            n_headlines=("n_headlines", "sum"),
        )
        .reset_index()
    )
    market["index_0_100"] = ((market["sentiment"] + 1.0) * 50.0).clip(0.0, 100.0)
    market["standardised_sentiment"] = (
        market["sentiment"] - market["sentiment"].mean()
    ) / market["sentiment"].std(ddof=1)
    market["news_available"] = market["n_tickers"].gt(0)
    market["model"] = "vader_finance_enhanced"
    result["market_index"] = market
    return result


def _run_fusion(
    state: dict[str, Any],
    funds: dict[str, Any],
    sentiment: dict[str, Any],
) -> dict[str, Any]:
    base = funds["fund_results"]["equity_min_variance"]
    enhanced_sector = sentiment["sector_index"].loc[
        sentiment["sector_index"]["model"].eq("vader_finance_enhanced")
    ].copy()
    return evaluate_fusion_variants(
        base["weights"],
        state["equity_returns"],
        enhanced_sector,
        window=60,
        min_periods=20,
    )


def _current_holdings(fund_weights: pd.DataFrame) -> pd.DataFrame:
    latest = fund_weights.groupby("fund_id")["effective_date"].transform("max")
    current = fund_weights.loc[fund_weights["effective_date"].eq(latest)].copy()
    current["rank"] = current.groupby("fund_id")["weight"].rank(
        method="first", ascending=False
    ).astype(int)
    return current.sort_values(["fund_id", "rank"], kind="stable").reset_index(drop=True)


def _write_data_and_tables(
    state: dict[str, Any],
    funds: dict[str, Any],
    sentiment: dict[str, Any],
    fusion: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    fund_returns = funds["fund_returns"][
        [
            "date", "fund_id", "asset_family", "method",
            "daily_return", "growth_of_1", "drawdown",
        ]
    ]
    fund_weights = funds["fund_weights"]
    sector_index = sentiment["sector_index"][
        [
            "date", "sector", "sentiment", "sentiment_lag1", "n_tickers",
            "n_headlines", "news_available", "model",
        ]
    ]
    metrics = funds["metrics"][
        [
            "fund_id", "asset_family", "method", "annualised_return",
            "annualised_volatility", "sharpe", "max_drawdown", "turnover",
            "first_oos_date", "last_oos_date", "n_oos_days", "n_rebalances",
        ]
    ]
    current = _current_holdings(fund_weights)

    fusion_returns = pd.concat(
        [daily.assign(variant=name) for name, daily in fusion["returns"].items()],
        ignore_index=True,
    )[["date", "variant", "daily_return", "growth_of_1", "drawdown"]]
    fusion_weights = pd.concat(
        [weights.assign(variant=name) for name, weights in fusion["weights"].items()],
        ignore_index=True,
    )

    fund_returns.to_csv(DATA_DIR / "fund_returns.csv", index=False)
    fund_weights.to_csv(DATA_DIR / "fund_weights.csv", index=False)
    sector_index.to_csv(DATA_DIR / "sector_sentiment_index.csv", index=False)
    sentiment["market_index"].to_csv(DATA_DIR / "market_sentiment_index.csv", index=False)
    fusion_returns.to_csv(DATA_DIR / "fusion_returns.csv", index=False)
    fusion_weights.to_csv(DATA_DIR / "fusion_weights.csv", index=False)

    metrics.to_csv(TABLE_DIR / "performance_metrics.csv", index=False)
    current.to_csv(TABLE_DIR / "current_holdings.csv", index=False)
    funds["backtest_audit"].to_csv(TABLE_DIR / "backtest_audit.csv", index=False)
    fusion["metrics"].to_csv(TABLE_DIR / "fusion_comparison.csv", index=False)
    sentiment["summary"].to_csv(TABLE_DIR / "sentiment_model_comparison.csv", index=False)
    sentiment["review_sample"].to_csv(
        TABLE_DIR / "sentiment_manual_review_sample.csv", index=False
    )
    sentiment["lexicon_candidates"].to_csv(
        TABLE_DIR / "finance_lexicon_candidates.csv", index=False
    )
    pd.DataFrame(
        [{"check": key, "count": value} for key, value in state["foundation_audit"].items()]
    ).to_csv(TABLE_DIR / "foundation_reproduction_audit.csv", index=False)

    return {
        "fund_returns": fund_returns,
        "fund_weights": fund_weights,
        "sector_index": sector_index,
        "metrics": metrics,
        "current_holdings": current,
        "fusion_returns": fusion_returns,
    }


def _figure_metrics_table(metrics: pd.DataFrame) -> pathlib.Path:
    display = metrics.copy()
    display["Fund"] = display["asset_family"].map(FAMILY_LABELS) + " - " + display["method"].map(METHOD_LABELS)
    for column in ("annualised_return", "annualised_volatility", "max_drawdown", "turnover"):
        display[column] = display[column].map(lambda value: f"{value:.1%}")
    display["sharpe"] = display["sharpe"].map(lambda value: f"{value:.2f}")
    display = display[
        ["Fund", "annualised_return", "annualised_volatility", "sharpe", "max_drawdown", "turnover"]
    ]
    display.columns = ["Fund", "Ann. return", "Ann. vol", "Sharpe", "Max drawdown", "Turnover"]

    fig, ax = plt.subplots(figsize=(14, 6.8))
    ax.axis("off")
    table = ax.table(
        cellText=display.values,
        colLabels=display.columns,
        loc="center",
        cellLoc="center",
        colWidths=[0.30, 0.14, 0.14, 0.11, 0.16, 0.15],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.45)
    for (row, _), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor(ACCENT)
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#EEEAE0")
    ax.set_title(
        "Table - OOS performance metrics across 12 systematic funds\n"
        "2021-01 to 2023-12; rf=0, baseline transaction cost=0",
        pad=18,
    )
    path = FIGURE_DIR / "performance_metrics_table.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_growth(fund_returns: pd.DataFrame) -> pathlib.Path:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.7), sharey=False)
    for ax, family in zip(axes, ("equity", "crypto", "combined")):
        subset = fund_returns.loc[fund_returns["asset_family"].eq(family)]
        for method in SUPPORTED_METHODS:
            line = subset.loc[subset["method"].eq(method)]
            ax.plot(
                pd.to_datetime(line["date"]), line["growth_of_1"],
                color=METHOD_COLORS[method], label=METHOD_LABELS[method], linewidth=1.6,
            )
        ax.axhline(1.0, color="#555555", linewidth=0.8, alpha=0.6)
        ax.set_title(FAMILY_LABELS[family])
        ax.set_xlabel("Date")
        ax.set_ylabel("Growth of $1")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=True)
    fig.suptitle("Growth of $1 by asset family and method - OOS period 2021-2023")
    fig.tight_layout(rect=[0, 0.10, 1, 0.94])
    path = FIGURE_DIR / "growth_of_1_comparison.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_drawdown(fund_returns: pd.DataFrame) -> pathlib.Path:
    fig, ax = plt.subplots(figsize=(12, 6.2))
    family_colors = {
        "equity": asset_class_color("equity"),
        "crypto": asset_class_color("crypto"),
        "combined": ACCENT_ALT,
    }
    subset = fund_returns.loc[fund_returns["method"].eq("min_variance")]
    family_styles = {"equity": "-", "crypto": "-", "combined": "--"}
    for family in ("equity", "crypto", "combined"):
        line = subset.loc[subset["asset_family"].eq(family)]
        ax.plot(
            pd.to_datetime(line["date"]),
            line["drawdown"],
            color=family_colors[family],
            linestyle=family_styles[family],
            label=FAMILY_LABELS[family],
        )
    ax.fill_between(
        pd.to_datetime(subset.loc[subset["asset_family"].eq("equity"), "date"]),
        subset.loc[subset["asset_family"].eq("equity"), "drawdown"],
        0,
        color=family_colors["equity"],
        alpha=0.08,
    )
    ax.set_title("Minimum-variance fund drawdowns by asset family - OOS 2021-2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown from prior peak")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.legend()
    path = FIGURE_DIR / "drawdown_min_variance.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_weights(fund_weights: pd.DataFrame) -> pathlib.Path:
    combined = fund_weights.loc[fund_weights["fund_id"].str.startswith("combined_")].copy()
    combined["allocation_group"] = np.where(
        combined["asset_class"].eq("crypto"), "Crypto", combined["sector"]
    )
    group_order = sorted(combined.loc[combined["allocation_group"].ne("Crypto"), "allocation_group"].dropna().unique()) + ["Crypto"]
    colors = [sector_color(group) if group != "Crypto" else asset_class_color("crypto") for group in group_order]
    fig, axes = plt.subplots(2, 2, figsize=(16, 9), sharex=True, sharey=True)
    for ax, method in zip(axes.flat, SUPPORTED_METHODS):
        subset = combined.loc[combined["fund_id"].eq(f"combined_{method}")]
        exposure = subset.pivot_table(
            index="effective_date", columns="allocation_group", values="weight", aggfunc="sum", fill_value=0
        ).reindex(columns=group_order, fill_value=0)
        ax.stackplot(
            pd.to_datetime(exposure.index),
            *[exposure[column].to_numpy() for column in group_order],
            labels=group_order,
            colors=colors,
            alpha=0.88,
        )
        ax.set_title(METHOD_LABELS[method])
        ax.set_ylabel("Portfolio weight")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.set_ylim(0, 1)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, fontsize=8, frameon=True)
    fig.suptitle("Combined-fund sector and crypto weights over time - 36 monthly OOS rebalances")
    fig.tight_layout(rect=[0, 0.10, 1, 0.94])
    path = FIGURE_DIR / "combined_weights_over_time.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_sharpe(metrics: pd.DataFrame) -> pathlib.Path:
    fig, ax = plt.subplots(figsize=(12, 6.4))
    x = np.arange(3)
    width = 0.19
    families = ("equity", "crypto", "combined")
    for index, method in enumerate(SUPPORTED_METHODS):
        values = [
            metrics.loc[
                metrics["asset_family"].eq(family) & metrics["method"].eq(method), "sharpe"
            ].iloc[0]
            for family in families
        ]
        ax.bar(x + (index - 1.5) * width, values, width, color=METHOD_COLORS[method], label=METHOD_LABELS[method])
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set_xticks(x, [FAMILY_LABELS[family] for family in families])
    ax.set_ylabel("Annualised Sharpe ratio (rf=0)")
    ax.set_title("OOS Sharpe ratio across 12 funds - 2021-2023")
    ax.legend(ncol=2)
    path = FIGURE_DIR / "sharpe_by_fund.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_sentiment(sector_index: pd.DataFrame) -> pathlib.Path:
    enhanced = sector_index.loc[sector_index["model"].eq("vader_finance_enhanced")].copy()
    sectors = sorted(enhanced["sector"].unique())
    fig, axes = plt.subplots(2, 5, figsize=(18, 8), sharex=True, sharey=True)
    for ax, sector in zip(axes.flat, sectors):
        subset = enhanced.loc[enhanced["sector"].eq(sector)].sort_values("date")
        dates = pd.to_datetime(subset["date"])
        smooth = subset["sentiment"].rolling(20, min_periods=5).mean()
        ax.plot(dates, subset["sentiment"], color=sector_color(sector), alpha=0.18, linewidth=0.7)
        ax.plot(dates, smooth, color=sector_color(sector), linewidth=1.5)
        ax.axhline(0, color="#555555", linewidth=0.7, alpha=0.6)
        ax.set_title(sector)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes[:, 0]:
        ax.set_ylabel("VADER compound")
    fig.suptitle(
        "Finance-enhanced VADER sector sentiment - daily (faint) and 20-day mean, 2020-2023"
    )
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    path = FIGURE_DIR / "sector_sentiment_timeseries.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_fusion(fusion_returns: pd.DataFrame) -> pathlib.Path:
    fig, ax = plt.subplots(figsize=(12, 6.4))
    for variant in ("base", "momentum", "contrarian"):
        subset = fusion_returns.loc[fusion_returns["variant"].eq(variant)]
        label = {
            "base": "Base minimum variance",
            "momentum": "Momentum tilt (lambda=+1)",
            "contrarian": "Contrarian tilt (lambda=-1)",
        }[variant]
        ax.plot(pd.to_datetime(subset["date"]), subset["growth_of_1"], color=FUSION_COLORS[variant], label=label)
    ax.axhline(1, color="#555555", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.set_title("Sentiment fusion before vs after - equity minimum-variance fund, OOS 2021-2023")
    ax.legend()
    path = FIGURE_DIR / "fusion_before_after.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def _write_figures(outputs: dict[str, pd.DataFrame]) -> list[pathlib.Path]:
    return [
        _figure_metrics_table(outputs["metrics"]),
        _figure_growth(outputs["fund_returns"]),
        _figure_drawdown(outputs["fund_returns"]),
        _figure_weights(outputs["fund_weights"]),
        _figure_sharpe(outputs["metrics"]),
        _figure_sentiment(outputs["sector_index"]),
        _figure_fusion(outputs["fusion_returns"]),
    ]


def main() -> None:
    apply_style()
    for directory in (DATA_DIR, TABLE_DIR, FIGURE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    print("[1/5] Rebuilding Part A data foundation...")
    state = _prepare_foundation()
    print("[2/5] Running 12 expanding-window OOS funds...")
    funds = _run_funds(state)
    print("[3/5] Scoring plain and finance-enhanced VADER sentiment...")
    sentiment = _run_sentiment(state)
    print("[4/5] Evaluating fixed base/momentum/contrarian fusion variants...")
    fusion = _run_fusion(state, funds, sentiment)
    print("[5/5] Writing app/report CSVs and self-contained figures...")
    outputs = _write_data_and_tables(state, funds, sentiment, fusion)
    figures = _write_figures(outputs)

    print("\nBuild complete.")
    for name, frame in outputs.items():
        print(f"{name}: {len(frame):,} rows")
    print(f"figures: {len(figures)}")
    print(f"funds: {outputs['metrics']['fund_id'].nunique()}")
    print(
        "first OOS dates: "
        + str(
            outputs["metrics"].groupby("asset_family")["first_oos_date"]
            .first().dt.date.to_dict()
        )
    )
    print("fusion metrics:")
    print(fusion["metrics"].to_string(index=False))
    print("sentiment neutral rates:")
    print(sentiment["summary"].to_string(index=False))
    for path in figures:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
