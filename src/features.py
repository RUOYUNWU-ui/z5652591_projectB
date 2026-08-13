"""Station 2 - your features: return features and headline text assembly.

Build your return (and optional risk) features here, and assemble the headlines
into a daily text panel. Part A is assembly only - scoring the text into sentiment
(and lagging the signal) is the Station 3 model, built in Part B, not here.
"""
import pandas as pd


def daily_returns(prices: pd.DataFrame, price_col: str = "adjClose") -> pd.DataFrame:
    """Compute the daily simple-return feature independently for each ticker.

    Daily returns are the one feature required by the Part B portfolio
    optimiser. The function remains calendar-agnostic so it works for both
    equity and cryptocurrency price panels; calendar alignment is handled in
    ``calendar_merge.py``.

    Parameters
    ----------
    prices
        Long-format price observations containing ``ticker``, ``date`` and the
        selected price column.
    price_col
        Price field used to calculate returns. Defaults to adjusted close so
        equity splits and distributions are reflected appropriately.

    Returns
    -------
    pandas.DataFrame
        Long-format observations with ``ticker``, ``date`` and
        ``daily_return`` columns.
    """
    required_columns = {"ticker", "date", price_col}
    missing_columns = required_columns.difference(prices.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"prices is missing required columns: {missing_list}")

    returns = prices.loc[:, ["ticker", "date", price_col]].copy()
    returns = returns.sort_values(["ticker", "date"], kind="stable")
    returns["daily_return"] = returns.groupby("ticker", sort=False)[
        price_col
    ].pct_change(fill_method=None)

    # The first observation for each ticker has no prior price, so its return is
    # undefined. Drop these NaNs to give the optimiser only observed returns.
    returns = returns.dropna(subset=["daily_return"])
    return returns.loc[:, ["ticker", "date", "daily_return"]].reset_index(drop=True)


def assemble_headline_panel(headlines: pd.DataFrame) -> pd.DataFrame:
    """Assemble mapped raw headlines into a daily ticker-sector text panel.

    The input is expected to have already been deduplicated and mapped to the
    equity trading calendar by the helpers in ``calendar_merge.py``. Original
    title strings are collected into lists without lowercasing, punctuation
    removal, stopword removal or other text transformation.

    Sentiment scoring and signal lagging are built in Part B, Station 3 — this
    function only assembles and date-aligns the raw text.

    Parameters
    ----------
    headlines
        Deduplicated and trading-day-mapped news observations containing at
        least ``trading_day``, ``ticker``, ``sector`` and ``title``.

    Returns
    -------
    pandas.DataFrame
        One row per trading-day, ticker and sector, with the headline count and
        a list of the original raw titles.
    """
    required_columns = {"trading_day", "ticker", "sector", "title"}
    missing_columns = required_columns.difference(headlines.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"headlines is missing required columns: {missing_list}")

    panel_source = headlines.loc[
        :, ["trading_day", "ticker", "sector", "title"]
    ].copy()
    panel_source["trading_day"] = (
        pd.to_datetime(panel_source["trading_day"], utc=True)
        .dt.tz_localize(None)
        .dt.normalize()
    )
    # Word count per headline (whitespace tokens, matching the "token = one
    # word" convention from Week 7's text glossary) - computed on the raw
    # title so it never touches text_raw itself, just like n_headlines below.
    panel_source["n_words"] = (
        panel_source["title"].fillna("").astype(str).str.split().apply(len)
    )

    # Keep title values exactly as supplied. A list preserves casing and
    # punctuation that VADER may use later in Part B.
    panel = (
        panel_source.groupby(
            ["trading_day", "ticker", "sector"],
            sort=False,
            dropna=False,
        )
        .agg(
            n_headlines=("title", "size"),
            headlines=("title", list),
            mean_n_words=("n_words", "mean"),
        )
        .reset_index()
    )

    return panel.sort_values(
        ["trading_day", "sector", "ticker"], kind="stable"
    ).reset_index(drop=True)


def news_coverage(
    headline_panel: pd.DataFrame, trading_dates: pd.Series | pd.Index
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Share of equity trading days on which each ticker, and each sector
    (pooling its five tickers), carries at least one headline.

    Taught in Week 7 on this exact news file: a single stock covers as few as
    39% of trading days (one averages 72%), but pooling five stocks into a
    sector lifts coverage to 91-99.7% - the stated reason the project builds
    each sentiment index at the sector level rather than the stock level.
    This reproduces that statistic on the assembled Part A panel so the claim
    is checked, not just cited.
    """
    calendar = pd.DatetimeIndex(sorted(pd.Series(trading_dates).unique()))
    n_days = len(calendar)

    by_ticker = (
        headline_panel.groupby("ticker")["trading_day"]
        .nunique()
        .rename("days_covered")
        .reset_index()
    )
    by_ticker["pct_days_covered"] = round(100 * by_ticker["days_covered"] / n_days, 1)

    by_sector = (
        headline_panel.groupby("sector")["trading_day"]
        .nunique()
        .rename("days_covered")
        .reset_index()
    )
    by_sector["pct_days_covered"] = round(100 * by_sector["days_covered"] / n_days, 1)

    return (
        by_ticker.sort_values("pct_days_covered").reset_index(drop=True),
        by_sector.sort_values("pct_days_covered").reset_index(drop=True),
    )
