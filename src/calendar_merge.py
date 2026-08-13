"""Calendar alignment helpers for Part A return and headline panels.

The functions in this module keep market-price return construction separate
from calendar alignment and make all date-handling choices explicit.
"""

import pandas as pd


def combine_equity_crypto_returns(
    equities_clean: pd.DataFrame, crypto_clean: pd.DataFrame
) -> pd.DataFrame:
    """Build a long equity-plus-crypto return panel on equity trading dates.

    Daily simple returns are calculated independently within the full equity
    and crypto panels before any calendar alignment. Crypto returns are then
    left-merged onto the equity trading calendar, intentionally excluding
    weekend-only crypto observations.

    Parameters
    ----------
    equities_clean
        Clean equity prices with ``ticker``, ``date``, ``adjClose`` and
        ``sector`` columns.
    crypto_clean
        Clean crypto prices with ``ticker``, ``date`` and ``adjClose`` columns.

    Returns
    -------
    pandas.DataFrame
        Long-format panel with columns ``date``, ``ticker``, ``asset_class``,
        ``sector`` and ``daily_return``.
    """
    equities = equities_clean.copy()
    crypto = crypto_clean.copy()

    equities["date"] = (
        pd.to_datetime(equities["date"], utc=True)
        .dt.tz_localize(None)
        .dt.normalize()
    )
    crypto["date"] = (
        pd.to_datetime(crypto["date"], utc=True)
        .dt.tz_localize(None)
        .dt.normalize()
    )

    # Returns must be calculated on each asset's native calendar first. Merging
    # price levels before differencing would create spurious crypto returns when
    # weekend dates disappear from the equity calendar.
    equities = equities.sort_values(["ticker", "date"], kind="stable")
    equities["daily_return"] = equities.groupby("ticker", sort=False)[
        "adjClose"
    ].pct_change(fill_method=None)

    crypto = crypto.sort_values(["ticker", "date"], kind="stable")
    crypto["daily_return"] = crypto.groupby("ticker", sort=False)[
        "adjClose"
    ].pct_change(fill_method=None)

    equity_calendar = pd.DatetimeIndex(
        equities["date"].dropna().unique()
    ).sort_values()

    equity_returns = equities.loc[
        :, ["date", "ticker", "sector", "daily_return"]
    ].copy()
    equity_returns["asset_class"] = "equity"

    # Create an equity-date-by-crypto grid, then left-merge returns that were
    # already calculated on the full seven-day crypto calendar. Weekend-only
    # crypto dates are absent from the base grid and are intentionally dropped.
    crypto_tickers = pd.Index(crypto["ticker"].dropna().unique()).sort_values()
    crypto_base = pd.MultiIndex.from_product(
        [equity_calendar, crypto_tickers], names=["date", "ticker"]
    ).to_frame(index=False)
    crypto_returns = crypto_base.merge(
        crypto.loc[:, ["date", "ticker", "daily_return"]],
        on=["date", "ticker"],
        how="left",
        validate="one_to_one",
    )
    crypto_returns["asset_class"] = "crypto"
    crypto_returns["sector"] = pd.NA

    column_order = ["date", "ticker", "asset_class", "sector", "daily_return"]
    combined = pd.concat(
        [equity_returns[column_order], crypto_returns[column_order]],
        ignore_index=True,
    )
    return combined.sort_values(
        ["date", "asset_class", "ticker"], kind="stable"
    ).reset_index(drop=True)


def dedupe_news_headlines(news_raw: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Normalise news dates and remove exact duplicate headlines.

    Dates are converted to UTC first, then made timezone-naive so they can be
    compared with the price panels. A duplicate requires the same ticker,
    calendar date and title; different headlines on the same ticker-date are
    genuine observations and remain in the data.

    Returns
    -------
    tuple[pandas.DataFrame, int]
        The deduplicated news frame and the number of duplicate rows removed.
    """
    news = news_raw.copy()
    news["date"] = (
        pd.to_datetime(news["date"], utc=True)
        .dt.normalize()
        .dt.tz_localize(None)
    )

    duplicate_mask = news.duplicated(
        subset=["ticker", "date", "title"], keep="first"
    )
    duplicates_dropped_count = int(duplicate_mask.sum())
    deduped = news.loc[~duplicate_mask].copy().reset_index(drop=True)
    return deduped, duplicates_dropped_count


def map_headline_to_trading_day(
    news_deduped: pd.DataFrame, equity_trading_calendar
) -> tuple[pd.DataFrame, int]:
    """Map each headline to its same or next available equity trading day.

    ``searchsorted(..., side="left")`` selects the first trading date greater
    than or equal to a headline date. Headlines later than the final calendar
    date have no valid forward mapping, so they are dropped and counted.

    Parameters
    ----------
    news_deduped
        Deduplicated news with a ``date`` column.
    equity_trading_calendar
        Array-like collection of equity trading dates.

    Returns
    -------
    tuple[pandas.DataFrame, int]
        News with a new ``trading_day`` column and the number of headlines
        dropped because they occur after the final trading date.
    """
    calendar = pd.DatetimeIndex(
        pd.to_datetime(equity_trading_calendar, utc=True)
    ).tz_localize(None).normalize().unique().sort_values()
    if calendar.empty:
        raise ValueError("equity_trading_calendar must contain at least one date")

    news = news_deduped.copy()
    news["date"] = (
        pd.to_datetime(news["date"], utc=True)
        .dt.normalize()
        .dt.tz_localize(None)
    )
    if news["date"].isna().any():
        raise ValueError("news_deduped contains missing or invalid dates")

    positions = calendar.searchsorted(news["date"].to_numpy(), side="left")
    within_calendar = positions < len(calendar)
    dropped_after_calendar_count = int((~within_calendar).sum())

    # Rows beyond the last trading date cannot be mapped forward and are
    # deliberately removed rather than assigned to a nonexistent date.
    mapped = news.loc[within_calendar].copy()
    mapped["trading_day"] = calendar.take(positions[within_calendar]).to_numpy()
    mapped = mapped.reset_index(drop=True)

    return mapped, dropped_after_calendar_count
