"""Innovation extension (Part A): sector news attention vs. realized volatility.

Purely descriptive, not predictive - this is Station 2 exploration, not a
Station 3 trading signal. It correlates how MUCH a sector is covered in the
news (headline volume - a count, not a sentiment score) with how volatile
that sector's equity returns were in the same week. No look-ahead concern
applies because nothing here forms weights, scores sentiment, or feeds a
backtest; it only describes a contemporaneous relationship in the cleaned
Part A data, motivating why a later sentiment/attention signal (Part B)
might carry information at all.

Weekly (not daily) buckets are used because a single trading day's headline
count is a noisy, low-information measure - weekly aggregation is closer to
the natural cadence of a news cycle and gives each sector-week enough
trading days (~5) to compute a realized volatility from.
"""
from __future__ import annotations

import pandas as pd


def sector_news_attention_vs_volatility(
    headline_panel: pd.DataFrame, equities: pd.DataFrame, equity_returns: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Correlate weekly sector headline volume with weekly sector realized volatility.

    Method
    ------
    1. Weekly sector news volume: sum ``n_headlines`` across all tickers in a
       sector within each ISO week (``headline_panel`` already carries one row
       per trading_day x ticker x sector).
    2. Weekly sector realized volatility: build an equal-weight sector proxy
       return each day (mean of that day's ticker-level daily returns for
       tickers in the sector), then take the standard deviation of that daily
       proxy return within each week:

           sector_vol_w = std_t in w ( mean_i in sector r_{i,t} )

    3. Correlation: for each sector, and pooled across all sectors, the
       Pearson correlation between weekly news volume and weekly volatility.

    Returns
    -------
    (summary_by_sector, weekly_panel) - the per-sector correlation summary
    (written to results/tables/) and the underlying weekly (sector, week,
    n_headlines, weekly_vol) panel used to build the figure.
    """
    news_weekly = (
        headline_panel.groupby(["sector", pd.Grouper(key="trading_day", freq="W")])["n_headlines"]
        .sum()
        .reset_index()
        .rename(columns={"trading_day": "week"})
    )

    sector_map = equities[["ticker", "sector"]].drop_duplicates()
    returns_with_sector = equity_returns.merge(sector_map, on="ticker", how="left")
    sector_daily_proxy = (
        returns_with_sector.groupby(["sector", "date"])["daily_return"].mean().reset_index()
    )
    vol_weekly = (
        sector_daily_proxy.groupby(["sector", pd.Grouper(key="date", freq="W")])["daily_return"]
        .std()
        .reset_index()
        .rename(columns={"date": "week", "daily_return": "weekly_vol"})
    )

    weekly_panel = news_weekly.merge(vol_weekly, on=["sector", "week"], how="inner").dropna(
        subset=["n_headlines", "weekly_vol"]
    )

    rows = []
    for sector, grp in weekly_panel.groupby("sector"):
        rows.append({
            "sector": sector,
            "n_weeks": len(grp),
            "avg_weekly_headlines": grp["n_headlines"].mean(),
            "avg_weekly_vol": grp["weekly_vol"].mean(),
            "correlation_news_vol": grp["n_headlines"].corr(grp["weekly_vol"]),
        })
    summary = pd.DataFrame(rows).sort_values("correlation_news_vol", ascending=False).reset_index(drop=True)

    pooled_corr = weekly_panel["n_headlines"].corr(weekly_panel["weekly_vol"])
    summary = pd.concat([
        summary,
        pd.DataFrame([{
            "sector": "ALL (pooled)",
            "n_weeks": len(weekly_panel),
            "avg_weekly_headlines": weekly_panel["n_headlines"].mean(),
            "avg_weekly_vol": weekly_panel["weekly_vol"].mean(),
            "correlation_news_vol": pooled_corr,
        }]),
    ], ignore_index=True)

    return summary, weekly_panel
