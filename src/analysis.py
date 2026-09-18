"""Reusable analysis and summary functions for the Brisbane River water quality dataset.

Extracted from notebooks/02_exploratory_environmental_analysis.ipynb once this
logic had been used to identify and cross-validate real findings (most
notably the May 2024 turbidity event, later confirmed independently in SQL).
"""
import pandas as pd


def coefficient_of_variation(df, columns):
    """Return each column's coefficient of variation (std / mean), sorted descending.

    CV is a unit-independent way to compare relative variability across
    parameters measured on very different scales (e.g. pH vs turbidity).
    """
    cv = (df[columns].std() / df[columns].mean().abs()).sort_values(ascending=False)
    return cv


def daily_mean(df, column, timestamp_column="timestamp"):
    """Resample a column to a daily mean, indexed by date."""
    working = df.set_index(timestamp_column) if df.index.name != timestamp_column else df
    return working[column].resample("D").mean()


def flag_anomalous_days(daily_series, z_threshold=3.0):
    """Flag days whose value is more than z_threshold standard deviations
    from the series' own mean.

    This is the z-score anomaly method used in Notebook 2 to first identify
    the May 2024 turbidity event, later independently confirmed by two
    different SQL techniques. Returns a boolean Series aligned to daily_series.
    """
    z_scores = (daily_series - daily_series.mean()) / daily_series.std()
    return z_scores.abs() > z_threshold


def find_consecutive_streaks(flags, min_length=2):
    """Given a boolean Series indexed by date, find runs of consecutive True
    values at least min_length days long.

    Returns a DataFrame with one row per streak: start date, end date, and
    length in days. This is the Python equivalent of the SQL "reset group"
    streak-detection technique in sql/04_environmental_insights.sql.
    """
    flags = flags.sort_index()
    streaks = []
    current_start = None
    current_len = 0

    for date, is_flagged in flags.items():
        if is_flagged:
            if current_start is None:
                current_start = date
            current_len += 1
        else:
            if current_start is not None and current_len >= min_length:
                streaks.append((current_start, previous_date, current_len))
            current_start = None
            current_len = 0
        previous_date = date

    if current_start is not None and current_len >= min_length:
        streaks.append((current_start, previous_date, current_len))

    return pd.DataFrame(streaks, columns=["streak_start", "streak_end", "streak_length_days"])


def monthly_summary(df, columns, year_column="year", month_column="month"):
    """Return mean, min, and max of each column, grouped by year and month."""
    grouped = df.groupby([year_column, month_column])[columns]
    summary = grouped.agg(["mean", "min", "max"])
    return summary.round(2)


def seasonal_summary(df, columns, season_column="season"):
    """Return mean of each column, grouped by season, in Southern Hemisphere
    calendar order (Summer, Autumn, Winter, Spring) rather than alphabetical.
    """
    season_order = ["Summer", "Autumn", "Winter", "Spring"]
    summary = df.groupby(season_column, observed=True)[columns].mean().round(2)
    return summary.reindex([s for s in season_order if s in summary.index])


def strongest_correlation(df, columns):
    """Return the (column_a, column_b, r) triple with the strongest absolute
    Pearson correlation among the given columns, excluding self-correlation.
    """
    import numpy as np

    corr = df[columns].corr()
    upper_triangle_mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
    upper = corr.where(upper_triangle_mask)
    pairs = upper.stack()
    best = pairs.abs().idxmax()
    return best[0], best[1], float(pairs[best])
