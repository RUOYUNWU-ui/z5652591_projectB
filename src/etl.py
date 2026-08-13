"""Station 1 - your ETL: load and clean the data.

Load raw data through src.data_access (see context/DATA_GUIDE.md). Add your own
integrity checks. Do not commit data files.
"""
import numpy as np
import pandas as pd

from src import data_access


def impossible_price_check(
    df: pd.DataFrame, price_cols=("open", "high", "low", "close", "adjClose")
) -> pd.DataFrame:
    """Flag rows with a non-positive price, or high < low - an impossible quote.

    Taught explicitly in the Week 4 DFF lecture as one of Stage 1's four core
    checks, run on this exact 50-stock dataset ("Impossible prices. Are any
    prices zero or negative? (None in our data)"). This function lets that
    claim be verified on the actual loaded data rather than assumed.
    """
    price_cols = list(price_cols)
    bad_price = (df[price_cols] <= 0).any(axis=1)
    bad_range = df["high"] < df["low"]
    flagged = df.loc[bad_price | bad_range, ["ticker", "date"] + price_cols].copy()
    flagged["reason"] = np.where(
        bad_price.loc[flagged.index], "non-positive price", "high < low"
    )
    return flagged.reset_index(drop=True)


def completeness_check(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Null count and null rate per core column.

    Week 2's Stage-1 "error check" step asserts completeness (at most 5%
    missing) before anything else uses the table; this reports the same
    statistic for the columns each dataset actually needs, rather than
    asserting and crashing, since Part A documents findings.
    """
    rows = []
    for col in columns:
        n_null = int(df[col].isna().sum())
        rows.append({
            "column": col,
            "n_null": n_null,
            "pct_null": round(100 * n_null / len(df), 3) if len(df) else 0.0,
        })
    return pd.DataFrame(rows)


def load_clean_equities():
    """Load, clean, and audit the provided equity-price panel.

    Returns
    -------
    tuple
        ``(clean_equities, missing_date_summary, duplicates_dropped_count,
        outlier_candidates)`` where:

        * ``clean_equities`` contains one observation per ticker-date;
        * ``missing_date_summary`` reports each ticker's missing observations
          relative to the dates observed elsewhere in the full equity panel;
        * ``duplicates_dropped_count`` is the number of repeated ticker-date
          observations removed; and
        * ``outlier_candidates`` lists extreme returns for documentation. These
          observations remain in ``clean_equities``.

    Notes
    -----
    ``pandas.bdate_range`` only approximates an exchange calendar. To avoid
    treating market holidays as missing, the audit intersects business days
    with the union of dates actually observed in the full equity dataset.
    """
    raw = data_access.load_equity_prices()
    clean = raw.copy()

    # Standardise dates so calendar comparisons are not affected by timestamps.
    clean["date"] = pd.to_datetime(clean["date"]).dt.tz_localize(None).dt.normalize()

    # A duplicate is another observation with the same ticker-date key. Keep
    # the first occurrence, count the remainder, and remove them before audits.
    duplicate_mask = clean.duplicated(subset=["ticker", "date"], keep="first")
    duplicates_dropped_count = int(duplicate_mask.sum())
    clean = clean.loc[~duplicate_mask].copy()

    # The full-panel union reflects actual market closures more accurately than
    # a generic weekday calendar. For each ticker, restrict that union to its
    # own observed min-to-max span and to business days.
    full_panel_dates = pd.DatetimeIndex(clean["date"].dropna().unique()).sort_values()
    missing_date_records = []
    for ticker, ticker_frame in clean.groupby("ticker", sort=True):
        observed_dates = pd.DatetimeIndex(ticker_frame["date"].dropna().unique())
        if observed_dates.empty:
            missing_count = 0
        else:
            business_day_span = pd.bdate_range(
                start=observed_dates.min(), end=observed_dates.max()
            )
            expected_dates = full_panel_dates.intersection(business_day_span)
            missing_count = len(expected_dates.difference(observed_dates))

        missing_date_records.append(
            {"ticker": ticker, "missing_dates_count": int(missing_count)}
        )

    missing_date_summary = pd.DataFrame(
        missing_date_records, columns=["ticker", "missing_dates_count"]
    )

    # Sort within ticker before calculating simple adjusted-close returns.
    clean = clean.sort_values(["ticker", "date"], kind="stable").reset_index(drop=True)
    daily_return = clean.groupby("ticker", sort=False)["adjClose"].pct_change(
        fill_method=None
    )
    ticker_mean = daily_return.groupby(clean["ticker"]).transform("mean")
    ticker_std = daily_return.groupby(clean["ticker"]).transform("std")

    # Flag, but do not remove, observations more than five ticker-specific
    # standard deviations from the ticker's own average daily return.
    outlier_mask = ticker_std.gt(0) & daily_return.sub(ticker_mean).abs().gt(
        5 * ticker_std
    )
    outlier_candidates = clean.loc[outlier_mask, ["ticker", "date"]].copy()
    outlier_candidates["return"] = daily_return.loc[outlier_mask].to_numpy()
    outlier_candidates["flag_reason"] = (
        "|return - ticker mean| > 5 ticker standard deviations"
    )
    outlier_candidates = outlier_candidates.reset_index(drop=True)

    return (
        clean,
        missing_date_summary,
        duplicates_dropped_count,
        outlier_candidates,
    )


def load_clean_crypto():
    """Load, clean, and audit the provided cryptocurrency-price panel.

    Returns
    -------
    tuple
        ``(clean_crypto, dropped_2024_rows_count,
        duplicates_dropped_count, outlier_candidates)`` where the two counts
        record observations removed by the sample-end and duplicate checks,
        respectively. Candidate extreme returns are reported separately and
        remain in ``clean_crypto``.

    Notes
    -----
    Crypto trades seven days per week, so its annualisation convention is based
    on a 365-day calendar rather than equities' approximately 252 trading days.
    That distinction matters for later analysis, not for this cleaning function.
    """
    raw = data_access.load_crypto_prices()
    clean = raw.copy()

    # Standardise dates before applying the required inclusive sample end.
    clean["date"] = pd.to_datetime(clean["date"]).dt.tz_localize(None).dt.normalize()
    sample_end = pd.Timestamp("2023-12-31")
    after_sample_end = clean["date"].gt(sample_end)
    dropped_2024_rows_count = int(after_sample_end.sum())
    clean = clean.loc[~after_sample_end].copy()

    # Keep the first observation for each ticker-date key and count subsequent
    # occurrences so the removal can be reported in the integrity summary.
    duplicate_mask = clean.duplicated(subset=["ticker", "date"], keep="first")
    duplicates_dropped_count = int(duplicate_mask.sum())
    clean = clean.loc[~duplicate_mask].copy()

    # Sort within ticker before computing simple daily adjusted-close returns.
    clean = clean.sort_values(["ticker", "date"], kind="stable").reset_index(drop=True)
    daily_return = clean.groupby("ticker", sort=False)["adjClose"].pct_change(
        fill_method=None
    )
    ticker_mean = daily_return.groupby(clean["ticker"]).transform("mean")
    ticker_std = daily_return.groupby(clean["ticker"]).transform("std")

    # Flag extreme observations for review, but retain them in the clean panel.
    outlier_mask = ticker_std.gt(0) & daily_return.sub(ticker_mean).abs().gt(
        5 * ticker_std
    )
    outlier_candidates = clean.loc[outlier_mask, ["ticker", "date"]].copy()
    outlier_candidates["return"] = daily_return.loc[outlier_mask].to_numpy()
    outlier_candidates["flag_reason"] = (
        "|return - ticker mean| > 5 ticker standard deviations"
    )
    outlier_candidates = outlier_candidates.reset_index(drop=True)

    return (
        clean,
        dropped_2024_rows_count,
        duplicates_dropped_count,
        outlier_candidates,
    )
