"""SignalYield investor dashboard.

The deployed app is intentionally thin: it reads precomputed CSV artifacts
under ``results/`` and never runs VADER, an optimiser, or a fund backtest.
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.ticker import PercentFormatter

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.plot_style import (  # noqa: E402
    ACCENT,
    ACCENT_ALT,
    ACCENT_LINE,
    apply_style,
    sector_color,
)


st.set_page_config(
    page_title="SignalYield | Systematic Funds",
    page_icon="SY",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_style()

METHOD_LABELS = {
    "equal_weight": "Equal Weight",
    "min_variance": "Minimum Variance",
    "max_sharpe": "Maximum Sharpe",
    "risk_parity": "Risk Parity",
}
FAMILY_LABELS = {
    "equity": "Equity-only",
    "crypto": "Crypto-only",
    "combined": "Combined",
}
METHOD_COLORS = {
    "equal_weight": "#332288",
    "min_variance": "#117733",
    "max_sharpe": "#CC6677",
    "risk_parity": "#88CCEE",
}
FAMILY_STYLES = {"equity": "-", "crypto": "--", "combined": ":"}
FUSION_COLORS = {"base": ACCENT, "momentum": ACCENT_ALT, "contrarian": ACCENT_LINE}

st.markdown(
    """
    <style>
    .stApp {background-color: #FBF9F4;}
    [data-testid="stSidebar"] {background-color: #F0ECE2;}
    .sy-hero {padding: 1.4rem 1.6rem; border-radius: 14px; background: #2C3E50;
              color: white; margin-bottom: 1rem;}
    .sy-kicker {color: #E8C07D; letter-spacing: .08em; font-size: .8rem;
                font-weight: 700; text-transform: uppercase;}
    .sy-note {padding: .8rem 1rem; border-left: 4px solid #CC6677;
              background: #F5EFE8; border-radius: 4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_artifacts() -> dict[str, pd.DataFrame]:
    """Load only precomputed app artifacts from results/."""
    paths = {
        "returns": ROOT / "results" / "data" / "fund_returns.csv",
        "weights": ROOT / "results" / "data" / "fund_weights.csv",
        "sentiment": ROOT / "results" / "data" / "sector_sentiment_index.csv",
        "market_sentiment": ROOT / "results" / "data" / "market_sentiment_index.csv",
        "fusion_returns": ROOT / "results" / "data" / "fusion_returns.csv",
        "metrics": ROOT / "results" / "tables" / "performance_metrics.csv",
        "holdings": ROOT / "results" / "tables" / "current_holdings.csv",
        "fusion_metrics": ROOT / "results" / "tables" / "fusion_comparison.csv",
        "shrinkage": ROOT / "results" / "tables" / "shrinkage_comparison.csv",
        "costs": ROOT / "results" / "tables" / "transaction_cost_sensitivity.csv",
    }
    missing = [str(path.relative_to(ROOT)) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing precomputed artifacts: " + ", ".join(missing)
            + ". Run python scripts/run_part_b.py locally and commit results/."
        )
    data = {name: pd.read_csv(path) for name, path in paths.items()}
    for key in ("returns", "sentiment", "market_sentiment", "fusion_returns"):
        data[key]["date"] = pd.to_datetime(data[key]["date"])
    for key in ("weights", "holdings"):
        data[key]["effective_date"] = pd.to_datetime(data[key]["effective_date"])
        data[key]["rebalance_date"] = pd.to_datetime(data[key]["rebalance_date"])
    return data


def fund_name(fund_id: str) -> str:
    row = artifacts["metrics"].loc[artifacts["metrics"]["fund_id"].eq(fund_id)].iloc[0]
    return f"{FAMILY_LABELS[row['asset_family']]} - {METHOD_LABELS[row['method']]}"


def format_metrics_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    display["Fund"] = display["fund_id"].map(fund_name)
    display["Annual return"] = display["annualised_return"].map(lambda x: f"{x:.1%}")
    display["Annual volatility"] = display["annualised_volatility"].map(lambda x: f"{x:.1%}")
    display["Sharpe"] = display["sharpe"].map(lambda x: f"{x:.2f}")
    display["Max drawdown"] = display["max_drawdown"].map(lambda x: f"{x:.1%}")
    display["Avg. turnover"] = display["turnover"].map(lambda x: f"{x:.1%}")
    return display[
        ["Fund", "Annual return", "Annual volatility", "Sharpe", "Max drawdown", "Avg. turnover"]
    ]


def plot_growth(frame: pd.DataFrame, fund_ids: list[str]):
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for fund_id in fund_ids:
        line = frame.loc[frame["fund_id"].eq(fund_id)].sort_values("date")
        if line.empty:
            continue
        method = line["method"].iloc[0]
        family = line["asset_family"].iloc[0]
        ax.plot(
            line["date"], line["growth_of_1"],
            color=METHOD_COLORS[method], linestyle=FAMILY_STYLES[family],
            label=fund_name(fund_id), linewidth=1.7,
        )
    ax.axhline(1.0, color="#555555", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


def allocation_metrics(returns: pd.Series, periods_per_year: int) -> dict[str, float]:
    returns = returns.dropna()
    growth = (1 + returns).cumprod()
    years = len(returns) / periods_per_year
    volatility = returns.std(ddof=1) * np.sqrt(periods_per_year)
    drawdown = growth.div(growth.cummax()).sub(1)
    return {
        "return": growth.iloc[-1] ** (1 / years) - 1,
        "volatility": volatility,
        "sharpe": returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year),
        "drawdown": drawdown.min(),
        "growth": growth.iloc[-1],
    }


try:
    artifacts = load_artifacts()
except Exception as exc:
    st.error(str(exc))
    st.stop()


navigation = st.sidebar.radio(
    "Investor journey",
    [
        "Home", "Fund Comparison", "Fund Fact Sheet", "Allocation Builder",
        "Sentiment Analytics", "Robustness Lab",
    ],
)
st.sidebar.markdown("---")
st.sidebar.caption("Precomputed OOS evidence | Sample ends 2023-12-31")
st.sidebar.caption("SignalYield is an educational prototype, not an investment adviser.")


if navigation == "Home":
    st.markdown(
        """
        <div class="sy-hero">
          <div class="sy-kicker">Systematic multi-asset investing</div>
          <h1>SignalYield</h1>
          <p>Compare transparent equity, crypto and combined funds, inspect their
          walk-forward evidence, and place sector news sentiment in context.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Systematic funds", artifacts["metrics"]["fund_id"].nunique())
    col2.metric("Asset families", artifacts["metrics"]["asset_family"].nunique())
    col3.metric("Optimisation methods", artifacts["metrics"]["method"].nunique())
    col4.metric("Sentiment sectors", artifacts["sentiment"]["sector"].nunique())

    st.subheader("What the evidence represents")
    st.write(
        "Fund weights are re-estimated monthly on an expanding history and become "
        "effective on the following trading day. Equity and combined funds use a "
        "252-day initial window; crypto-only funds use 365 days. The displayed "
        "period is genuinely out of sample, beginning in January 2021."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### Four portfolio rules")
        st.write("Equal Weight, Minimum Variance, Maximum Sharpe and Risk Parity. All are long-only and fully invested, with no hidden exposure caps.")
    with right:
        st.markdown("#### News as context")
        st.write("Finance-enhanced VADER summarises raw equity headlines by sector. It is a noisy proxy, not a forecast or a substitute for risk analysis.")
    st.markdown(
        '<div class="sy-note"><b>Risk disclosure:</b> Historical simulations can lose value, '
        "crypto is especially volatile, and past performance does not predict future returns.</div>",
        unsafe_allow_html=True,
    )


elif navigation == "Fund Comparison":
    st.title("Fund Comparison")
    st.caption("Compare the 12 walk-forward OOS funds using the same 2021-2023 evidence base.")
    families = st.multiselect(
        "Asset families",
        options=list(FAMILY_LABELS),
        default=list(FAMILY_LABELS),
        format_func=lambda value: FAMILY_LABELS[value],
    )
    methods = st.multiselect(
        "Methods",
        options=list(METHOD_LABELS),
        default=list(METHOD_LABELS),
        format_func=lambda value: METHOD_LABELS[value],
    )
    selected_metrics = artifacts["metrics"].loc[
        artifacts["metrics"]["asset_family"].isin(families)
        & artifacts["metrics"]["method"].isin(methods)
    ]
    if selected_metrics.empty:
        st.warning("Select at least one asset family and one method.")
    else:
        st.dataframe(format_metrics_table(selected_metrics), hide_index=True, width="stretch")
        st.subheader("Growth of $1")
        fig = plot_growth(artifacts["returns"], selected_metrics["fund_id"].tolist())
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption("Solid = equity-only, dashed = crypto-only, dotted = combined. Colours identify methods.")


elif navigation == "Fund Fact Sheet":
    st.title("Fund Fact Sheet")
    fund_ids = artifacts["metrics"]["fund_id"].tolist()
    chosen = st.selectbox("Choose a fund", fund_ids, format_func=fund_name)
    metric = artifacts["metrics"].loc[artifacts["metrics"]["fund_id"].eq(chosen)].iloc[0]
    fund_returns = artifacts["returns"].loc[artifacts["returns"]["fund_id"].eq(chosen)].sort_values("date")
    holdings = artifacts["holdings"].loc[artifacts["holdings"]["fund_id"].eq(chosen)].sort_values("rank")

    st.subheader(fund_name(chosen))
    cols = st.columns(5)
    cols[0].metric("Annual return", f"{metric['annualised_return']:.1%}")
    cols[1].metric("Annual volatility", f"{metric['annualised_volatility']:.1%}")
    cols[2].metric("Sharpe (rf=0)", f"{metric['sharpe']:.2f}")
    cols[3].metric("Maximum drawdown", f"{metric['max_drawdown']:.1%}")
    cols[4].metric("Avg. turnover", f"{metric['turnover']:.1%}")

    left, right = st.columns(2)
    with left:
        fig, ax = plt.subplots(figsize=(7, 4.1))
        ax.plot(fund_returns["date"], fund_returns["growth_of_1"], color=METHOD_COLORS[metric["method"]])
        ax.axhline(1, color="#555555", linewidth=0.8)
        ax.set_title("Growth of $1")
        ax.set_xlabel("Date")
        ax.set_ylabel("Growth of $1")
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    with right:
        fig, ax = plt.subplots(figsize=(7, 4.1))
        ax.plot(fund_returns["date"], fund_returns["drawdown"], color=ACCENT_LINE)
        ax.fill_between(fund_returns["date"], fund_returns["drawdown"], 0, color=ACCENT_LINE, alpha=0.12)
        ax.set_title("Drawdown from prior peak")
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)

    st.markdown("#### Current target holdings")
    holdings_display = holdings[["ticker", "asset_class", "sector", "weight", "effective_date"]].copy()
    holdings_display["weight"] = holdings_display["weight"].map(lambda x: f"{x:.2%}")
    st.dataframe(holdings_display, hide_index=True, width="stretch", height=360)
    method_text = {
        "equal_weight": "allocates the same weight to every asset",
        "min_variance": "minimises estimated portfolio variance",
        "max_sharpe": "maximises estimated return per unit of risk with rf=0",
        "risk_parity": "targets an equal contribution to total portfolio risk",
    }[metric["method"]]
    st.info(
        f"Rule: {method_text}. Estimates use all available history before each "
        "monthly effective date; new long-only weights take effect on the next "
        f"trading day. Latest displayed target: {holdings['effective_date'].max().date()}."
    )


elif navigation == "Allocation Builder":
    st.title("Allocation Builder")
    st.caption("Combine the precomputed fund return histories; this does not rerun an optimiser.")
    all_funds = artifacts["metrics"]["fund_id"].tolist()
    default_funds = ["equity_risk_parity", "combined_equal_weight", "crypto_min_variance"]
    chosen_funds = st.multiselect(
        "Select funds",
        all_funds,
        default=[fund for fund in default_funds if fund in all_funds],
        format_func=fund_name,
    )
    if not chosen_funds:
        st.warning("Choose at least one fund to build an allocation.")
    else:
        allocations = {}
        suggested = 100.0 / len(chosen_funds)
        columns = st.columns(min(3, len(chosen_funds)))
        for index, fund_id in enumerate(chosen_funds):
            with columns[index % len(columns)]:
                allocations[fund_id] = st.number_input(
                    fund_name(fund_id) + " (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(suggested),
                    step=1.0,
                    key=f"allocation_{fund_id}",
                )
        total = sum(allocations.values())
        st.metric("Total allocation", f"{total:.2f}%")
        if not np.isclose(total, 100.0, atol=0.01, rtol=0.0):
            st.warning(
                f"Allocations currently total {total:.2f}%. Adjust them to exactly 100% "
                "before the historical simulation is shown."
            )
        else:
            selected = artifacts["returns"].loc[
                artifacts["returns"]["fund_id"].isin(chosen_funds),
                ["date", "fund_id", "daily_return"],
            ]
            matrix = selected.pivot(index="date", columns="fund_id", values="daily_return")
            matrix = matrix[chosen_funds].dropna(how="any")
            weights = pd.Series({fund: value / 100.0 for fund, value in allocations.items()})
            portfolio = matrix.mul(weights, axis=1).sum(axis=1)
            growth = (1 + portfolio).cumprod()
            chosen_families = set(
                artifacts["metrics"].set_index("fund_id").loc[chosen_funds, "asset_family"]
            )
            periods = 365 if chosen_families == {"crypto"} else 252
            stats = allocation_metrics(portfolio, periods)
            cols = st.columns(5)
            cols[0].metric("Annual return", f"{stats['return']:.1%}")
            cols[1].metric("Annual volatility", f"{stats['volatility']:.1%}")
            cols[2].metric("Sharpe (rf=0)", f"{stats['sharpe']:.2f}")
            cols[3].metric("Maximum drawdown", f"{stats['drawdown']:.1%}")
            cols[4].metric("Ending $1", f"${stats['growth']:.2f}")
            fig, ax = plt.subplots(figsize=(11, 5))
            ax.plot(growth.index, growth, color=ACCENT, linewidth=1.8)
            ax.axhline(1, color="#555555", linewidth=0.8)
            ax.set_title("Historical growth of the selected fund allocation")
            ax.set_xlabel("Date")
            ax.set_ylabel("Growth of $1")
            fig.tight_layout()
            st.pyplot(fig, width="stretch")
            plt.close(fig)
            st.caption(
                "Mixed allocations use dates shared by all selected funds. Fund returns "
                "and weights were precomputed; only the user's linear allocation is calculated here."
            )
        st.markdown(
            '<div class="sy-note"><b>Not personal financial advice.</b> This is a historical '
            "simulation using a fixed sample. It ignores your objectives, tax position, liquidity "
            "needs and future market changes.</div>",
            unsafe_allow_html=True,
        )


elif navigation == "Sentiment Analytics":
    st.title("Sentiment Analytics")
    st.caption("Headline sentiment is a noisy sector-level proxy, not a causal or predictive claim.")
    model = st.selectbox(
        "Sentiment model",
        ["vader_finance_enhanced", "vader_plain"],
        format_func=lambda value: "Finance-enhanced VADER" if "enhanced" in value else "Plain VADER",
    )
    sector = st.selectbox("Sector", sorted(artifacts["sentiment"]["sector"].unique()))
    subset = artifacts["sentiment"].loc[
        artifacts["sentiment"]["model"].eq(model)
        & artifacts["sentiment"]["sector"].eq(sector)
    ].sort_values("date")
    coverage = subset["news_available"].astype(str).str.lower().eq("true").mean()
    cols = st.columns(4)
    cols[0].metric("Trading-day coverage", f"{coverage:.1%}")
    cols[1].metric("Headlines", f"{int(subset['n_headlines'].sum()):,}")
    cols[2].metric("No-news days", int((~subset["news_available"].astype(str).str.lower().eq("true")).sum()))
    cols[3].metric("Latest index", f"{subset['sentiment'].dropna().iloc[-1]:+.3f}")

    smoothing = st.slider("Display smoothing (trading days)", 1, 60, 20)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(subset["date"], subset["sentiment"], color=sector_color(sector), alpha=0.18, linewidth=0.8, label="Daily")
    ax.plot(
        subset["date"],
        subset["sentiment"].rolling(smoothing, min_periods=max(1, smoothing // 4)).mean(),
        color=sector_color(sector), linewidth=1.8, label=f"{smoothing}-day mean",
    )
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set_title(f"{sector} sector sentiment, 2020-2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("VADER compound score")
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

    st.markdown("#### Market-wide context")
    market = artifacts["market_sentiment"].sort_values("date")
    latest_market = market.iloc[-1]
    left, right = st.columns([1, 3])
    left.metric("Latest 0-100 reading", f"{latest_market['index_0_100']:.1f}", help="50 is neutral; descriptive, not a trading signal.")
    with right:
        fig, ax = plt.subplots(figsize=(9, 2.8))
        ax.plot(market["date"], market["index_0_100"].rolling(20, min_periods=5).mean(), color=ACCENT_ALT)
        ax.axhline(50, color="#555555", linewidth=0.8)
        ax.set_ylabel("Index (0-100)")
        ax.set_xlabel("Date")
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)

    st.markdown("#### Does the sentiment tilt change the fund?")
    fusion_metrics = artifacts["fusion_metrics"].copy()
    fusion_display = fusion_metrics.copy()
    fusion_display["Annual return"] = fusion_display["annualised_return"].map(lambda x: f"{x:.1%}")
    fusion_display["Annual volatility"] = fusion_display["annualised_volatility"].map(lambda x: f"{x:.1%}")
    fusion_display["Sharpe"] = fusion_display["sharpe"].map(lambda x: f"{x:.2f}")
    fusion_display["Max drawdown"] = fusion_display["max_drawdown"].map(lambda x: f"{x:.1%}")
    st.dataframe(
        fusion_display[["variant", "lambda", "Annual return", "Annual volatility", "Sharpe", "Max drawdown"]],
        hide_index=True,
        width="stretch",
    )
    fig, ax = plt.subplots(figsize=(11, 5))
    for variant in ("base", "momentum", "contrarian"):
        line = artifacts["fusion_returns"].loc[
            artifacts["fusion_returns"]["variant"].eq(variant)
        ]
        ax.plot(line["date"], line["growth_of_1"], color=FUSION_COLORS[variant], label=variant.title())
    ax.set_title("Equity minimum-variance fund: base vs fixed sentiment tilts")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.info(
        "The +1 momentum and -1 contrarian directions were fixed before viewing "
        "the OOS outcomes and are both retained. No full-period parameter search was used."
    )


else:  # Robustness Lab
    st.title("Robustness Lab")
    st.caption(
        "Pre-specified checks ask whether key conclusions survive an alternative "
        "covariance estimator and plausible turnover costs. The canonical 12-fund "
        "results remain the sample-covariance, zero-cost baseline."
    )

    st.subheader("Covariance shrinkage")
    family = st.selectbox(
        "Asset family for shrinkage comparison",
        list(FAMILY_LABELS),
        format_func=lambda value: FAMILY_LABELS[value],
        key="robustness_family",
    )
    shrinkage = artifacts["shrinkage"].loc[
        artifacts["shrinkage"]["asset_family"].eq(family)
    ].copy()
    shrinkage["Method"] = shrinkage["method"].map(METHOD_LABELS)
    shrinkage["Estimator"] = shrinkage["covariance_estimator"].map(
        {"sample": "Sample covariance", "ledoit_wolf": "Ledoit-Wolf"}
    )
    shrinkage["Annual return"] = shrinkage["annualised_return"].map(
        lambda value: f"{value:.1%}"
    )
    shrinkage["Annual volatility"] = shrinkage["annualised_volatility"].map(
        lambda value: f"{value:.1%}"
    )
    shrinkage["Sharpe"] = shrinkage["sharpe"].map(lambda value: f"{value:.2f}")
    shrinkage["Sharpe change"] = shrinkage["delta_sharpe"].map(
        lambda value: f"{value:+.2f}"
    )
    st.dataframe(
        shrinkage[
            [
                "Method", "Estimator", "Annual return", "Annual volatility",
                "Sharpe", "Sharpe change",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
    st.info(
        "Ledoit-Wolf automatically estimates shrinkage inside each expanding "
        "window. It is an untuned robustness result, not a replacement selected "
        "after seeing out-of-sample performance."
    )

    st.subheader("Transaction-cost sensitivity")
    selected_fund = st.selectbox(
        "Fund for cost curve",
        artifacts["metrics"]["fund_id"].tolist(),
        format_func=fund_name,
    )
    costs = artifacts["costs"].loc[
        artifacts["costs"]["fund_id"].eq(selected_fund)
    ].sort_values("cost_bps")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(
        costs["cost_bps"], costs["sharpe"], marker="o", color=ACCENT,
        linewidth=1.8,
    )
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set_xlabel("One-way transaction cost (bps)")
    ax.set_ylabel("Annualised Sharpe ratio")
    ax.set_title(f"Cost sensitivity: {fund_name(selected_fund)}")
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    cost_display = costs[
        ["cost_bps", "annualised_return", "sharpe", "final_growth_of_1"]
    ].copy()
    cost_display["annualised_return"] = cost_display["annualised_return"].map(
        lambda value: f"{value:.1%}"
    )
    cost_display["sharpe"] = cost_display["sharpe"].map(
        lambda value: f"{value:.2f}"
    )
    cost_display["final_growth_of_1"] = cost_display[
        "final_growth_of_1"
    ].map(lambda value: f"${value:.2f}")
    cost_display.columns = [
        "Cost (bps)", "Annual return", "Sharpe", "Ending $1",
    ]
    st.dataframe(cost_display, hide_index=True, width="stretch")
    st.caption(
        "Costs are charged on post-launch rebalance turnover only. They do not "
        "feed back into weight formation, and taxes, spreads and market impact "
        "outside the fixed bps assumption remain unmodelled."
    )
