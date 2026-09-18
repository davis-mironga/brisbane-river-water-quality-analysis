"""Reusable data-cleaning functions for the Brisbane River water quality dataset.

Extracted from notebooks/01_data_understanding_cleaning.ipynb once the cleaning
logic there had been investigated and verified against the real dataset. These
functions are intended to be imported by future notebooks, scripts, or a
pipeline (e.g. the planned Google Cloud step) rather than duplicating this
logic inline again.
"""
from pathlib import Path

import pandas as pd

RAW_TO_CLEAN_COLUMNS = {
    "Timestamp": "timestamp",
    "Record number": "record_number",
    "Average Water Speed": "water_speed",
    "Average Water Direction": "water_direction",
    "Chlorophyll": "chlorophyll",
    "Chlorophyll [quality]": "chlorophyll_quality",
    "Temperature": "temperature",
    "Temperature [quality]": "temperature_quality",
    "Dissolved Oxygen": "dissolved_oxygen",
    "Dissolved Oxygen [quality]": "dissolved_oxygen_quality",
    "Dissolved Oxygen (%Saturation)": "dissolved_oxygen_pct_sat",
    "Dissolved Oxygen (%Saturation) [quality]": "dissolved_oxygen_pct_sat_quality",
    "pH": "ph",
    "pH [quality]": "ph_quality",
    "Salinity": "salinity",
    "Salinity [quality]": "salinity_quality",
    "Specific Conductance": "specific_conductance",
    "Specific Conductance [quality]": "specific_conductance_quality",
    "Turbidity": "turbidity",
    "Turbidity [quality]": "turbidity_quality",
}

MEASUREMENT_COLUMNS = [
    "water_speed", "water_direction", "chlorophyll", "temperature",
    "dissolved_oxygen", "dissolved_oxygen_pct_sat", "ph",
    "salinity", "specific_conductance", "turbidity",
]

SEASON_ORDER = ["Summer", "Autumn", "Winter", "Spring"]


def load_raw_data(raw_path, download_url=None):
    """Load the raw CSV, downloading it first if it isn't present locally."""
    raw_path = Path(raw_path)
    if not raw_path.exists():
        if download_url is None:
            raise FileNotFoundError(
                f"{raw_path} not found and no download_url was provided."
            )
        import urllib.request

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(download_url, raw_path)

    return pd.read_csv(raw_path)

def rename_columns(df):
    """Rename raw human-readable columns to clean snake_case names."""
    mapping = {k: v for k, v in RAW_TO_CLEAN_COLUMNS.items() if k in df.columns}
    return df.rename(columns=mapping)


def convert_timestamp(df, column="timestamp"):
    """Convert the timestamp column to a proper pandas datetime dtype."""
    df = df.copy()
    df[column] = pd.to_datetime(df[column])
    return df


def find_full_duplicates(df):
    """Return rows that are fully duplicated (every column identical)."""
    return df[df.duplicated(keep=False)]


def find_duplicate_record_numbers(df, column="record_number"):
    """Return rows whose record_number value appears more than once."""
    counts = df[column].value_counts()
    duplicated_ids = counts[counts > 1].index
    return df[df[column].isin(duplicated_ids)]


def validate_physical_ranges(df):
    """Check every measurement column against known-plausible physical ranges.

    Returns a dict of check name to count of rows failing that check. All
    values are expected to be 0 for a properly cleaned dataset.
    """
    results = {}

    if "ph" in df.columns:
        results["invalid_ph"] = int(((df["ph"] < 0) | (df["ph"] > 14)).sum())

    if "water_direction" in df.columns:
        results["invalid_water_direction"] = int(
            ((df["water_direction"] < 0) | (df["water_direction"] > 360)).sum()
        )

    if "dissolved_oxygen_pct_sat" in df.columns:
        results["implausible_do_saturation"] = int(
            (df["dissolved_oxygen_pct_sat"] > 200).sum()
        )

    negative_checks = [
        c for c in ["water_speed", "chlorophyll", "dissolved_oxygen",
                     "salinity", "specific_conductance", "turbidity"]
        if c in df.columns
    ]
    if negative_checks:
        negative_mask = (df[negative_checks] < 0).any(axis=1)
        results["negative_values"] = int(negative_mask.sum())

    return results


def add_time_features(df, timestamp_column="timestamp"):
    """Engineer year/month/day/hour/day_of_week/season columns from a timestamp.

    Season follows the Southern Hemisphere convention (Brisbane is in the
    Southern Hemisphere): Summer = Dec-Feb, Autumn = Mar-May, Winter = Jun-Aug,
    Spring = Sep-Nov -- the reverse of the Northern Hemisphere default.
    """
    df = df.copy()
    ts = df[timestamp_column]
    if not pd.api.types.is_datetime64_any_dtype(ts):
        ts = pd.to_datetime(ts)
        df[timestamp_column] = ts

    df["year"] = ts.dt.year
    df["month"] = ts.dt.month
    df["day"] = ts.dt.day
    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.day_name()
    df["season"] = df["month"].apply(_month_to_season)
    return df


def _month_to_season(month):
    if month in (12, 1, 2):
        return "Summer"
    if month in (3, 4, 5):
        return "Autumn"
    if month in (6, 7, 8):
        return "Winter"
    return "Spring"


def missingness_summary(df, columns=None):
    """Return missing-value count and percentage per column, sorted worst-first."""
    cols = columns if columns is not None else df.columns.tolist()
    missing_count = df[cols].isna().sum()
    missing_pct = (missing_count / len(df) * 100).round(2)
    summary = pd.DataFrame({"missing_count": missing_count, "missing_pct": missing_pct})
    return summary.sort_values("missing_pct", ascending=False)


def validate_cleaned_dataset(df, original_row_count):
    """Assert the core invariants a properly cleaned dataset must satisfy."""
    assert df.shape[0] == original_row_count, "Row count changed unexpectedly during cleaning"
    assert df["record_number"].is_unique, "record_number should be a unique key"
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"]), "timestamp should be a datetime dtype"
    assert df["season"].isna().sum() == 0, "every row should have a season"
    assert set(df["season"].unique()) == set(SEASON_ORDER)
