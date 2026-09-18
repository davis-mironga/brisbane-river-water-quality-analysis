"""Unit tests for src/cleaning.py.

Run with: pytest tests/test_cleaning.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import cleaning


@pytest.fixture
def sample_raw_df():
    """A small raw-format dataframe (original Kaggle column names) covering
    all four seasons, used across multiple tests below.
    """
    n = 400
    timestamps = pd.date_range("2023-08-04", periods=n, freq="12h")
    return pd.DataFrame({
        "Timestamp": timestamps.astype(str),
        "Record number": range(1000, 1000 + n),
        "Average Water Speed": np.random.uniform(0, 1, n),
        "Average Water Direction": np.random.uniform(0, 360, n),
        "Chlorophyll": np.random.uniform(0, 20, n),
        "Chlorophyll [quality]": np.nan,
        "Temperature": np.random.uniform(15, 28, n),
        "Temperature [quality]": np.nan,
        "Dissolved Oxygen": np.random.uniform(4, 9, n),
        "Dissolved Oxygen [quality]": np.nan,
        "Dissolved Oxygen (%Saturation)": np.random.uniform(50, 110, n),
        "Dissolved Oxygen (%Saturation) [quality]": np.nan,
        "pH": np.random.uniform(6.5, 8.5, n),
        "pH [quality]": np.nan,
        "Salinity": np.random.uniform(0, 30, n),
        "Salinity [quality]": np.nan,
        "Specific Conductance": np.random.uniform(100, 50000, n),
        "Specific Conductance [quality]": np.nan,
        "Turbidity": np.random.uniform(0, 50, n),
        "Turbidity [quality]": np.nan,
    })


@pytest.fixture
def sample_clean_df(sample_raw_df):
    """sample_raw_df, already renamed, timestamp-converted, and feature-engineered."""
    df = cleaning.rename_columns(sample_raw_df)
    df = cleaning.convert_timestamp(df)
    df = cleaning.add_time_features(df)
    return df


def test_rename_columns_produces_expected_names(sample_raw_df):
    df = cleaning.rename_columns(sample_raw_df)
    assert "timestamp" in df.columns
    assert "timestamp" in df.columns
    assert "record_number" in df.columns
    assert "dissolved_oxygen_pct_sat" in df.columns
    assert "Timestamp" not in df.columns
    assert "Dissolved Oxygen (%Saturation)" not in df.columns


def test_rename_columns_is_idempotent(sample_raw_df):
    """Renaming an already-renamed dataframe should not raise or change anything."""
    once = cleaning.rename_columns(sample_raw_df)
    twice = cleaning.rename_columns(once)
    assert list(once.columns) == list(twice.columns)


def test_measurement_columns_all_present_after_rename(sample_raw_df):
    df = cleaning.rename_columns(sample_raw_df)
    for col in cleaning.MEASUREMENT_COLUMNS:
        assert col in df.columns, f"expected measurement column {col} after renaming"


def test_convert_timestamp_produces_datetime_dtype(sample_raw_df):
    df = cleaning.rename_columns(sample_raw_df)
    assert not pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    df = cleaning.convert_timestamp(df)
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])


def test_convert_timestamp_preserves_values(sample_raw_df):
    df = cleaning.rename_columns(sample_raw_df)
    original_first = df["timestamp"].iloc[0]
    df = cleaning.convert_timestamp(df)
    assert df["timestamp"].iloc[0] == pd.Timestamp(original_first)


def test_convert_timestamp_does_not_mutate_input(sample_raw_df):
    df = cleaning.rename_columns(sample_raw_df)
    original_dtype = df["timestamp"].dtype
    cleaning.convert_timestamp(df)
    assert df["timestamp"].dtype == original_dtype, "input dataframe should not be mutated"


def test_find_full_duplicates_empty_on_clean_data(sample_clean_df):
    result = cleaning.find_full_duplicates(sample_clean_df)
    assert len(result) == 0


def test_find_full_duplicates_detects_injected_duplicate(sample_clean_df):
    df_with_dupe = pd.concat([sample_clean_df, sample_clean_df.iloc[[0]]], ignore_index=True)
    result = cleaning.find_full_duplicates(df_with_dupe)
    assert len(result) == 2


def test_find_duplicate_record_numbers_empty_on_clean_data(sample_clean_df):
    result = cleaning.find_duplicate_record_numbers(sample_clean_df)
    assert len(result) == 0


def test_find_duplicate_record_numbers_detects_injected_duplicate(sample_clean_df):
    df_with_dupe = pd.concat([sample_clean_df, sample_clean_df.iloc[[5]]], ignore_index=True)
    result = cleaning.find_duplicate_record_numbers(df_with_dupe)
    assert len(result) == 2
    assert result["record_number"].nunique() == 1


def test_missingness_summary_reports_zero_on_clean_data(sample_clean_df):
    summary = cleaning.missingness_summary(sample_clean_df, cleaning.MEASUREMENT_COLUMNS)
    assert (summary["missing_count"] == 0).all()
    assert (summary["missing_pct"] == 0).all()


def test_missingness_summary_detects_injected_missing_values(sample_clean_df):
    df = sample_clean_df.copy()
    df.loc[0:9, "temperature"] = np.nan
    summary = cleaning.missingness_summary(df, cleaning.MEASUREMENT_COLUMNS)
    assert summary.loc["temperature", "missing_count"] == 10
    expected_pct = round(10 / len(df) * 100, 2)
    assert summary.loc["temperature", "missing_pct"] == expected_pct


def test_missingness_summary_sorted_worst_first(sample_clean_df):
    df = sample_clean_df.copy()
    df.loc[0:49, "salinity"] = np.nan
    df.loc[0:4, "turbidity"] = np.nan
    summary = cleaning.missingness_summary(df, cleaning.MEASUREMENT_COLUMNS)
    assert summary.index[0] == "salinity"


def test_validate_physical_ranges_all_zero_on_clean_data(sample_clean_df):
    results = cleaning.validate_physical_ranges(sample_clean_df)
    assert all(count == 0 for count in results.values())


def test_validate_physical_ranges_detects_invalid_ph(sample_clean_df):
    df = sample_clean_df.copy()
    df.loc[0, "ph"] = 20
    results = cleaning.validate_physical_ranges(df)
    assert results["invalid_ph"] == 1


def test_validate_physical_ranges_detects_invalid_direction(sample_clean_df):
    df = sample_clean_df.copy()
    df.loc[0, "water_direction"] = 400
    results = cleaning.validate_physical_ranges(df)
    assert results["invalid_water_direction"] == 1


def test_validate_physical_ranges_detects_negative_values(sample_clean_df):
    df = sample_clean_df.copy()
    df.loc[0, "turbidity"] = -5
    results = cleaning.validate_physical_ranges(df)
    assert results["negative_values"] == 1


def test_add_time_features_creates_expected_columns(sample_clean_df):
    for col in ["year", "month", "day", "hour", "day_of_week", "season"]:
        assert col in sample_clean_df.columns


def test_add_time_features_southern_hemisphere_seasons(sample_raw_df):
    """August (Southern Hemisphere) must map to Winter, not Summer."""
    df = cleaning.rename_columns(sample_raw_df)
    df = cleaning.convert_timestamp(df)
    df = cleaning.add_time_features(df)
    august_rows = df[df["month"] == 8]
    assert (august_rows["season"] == "Winter").all()


def test_add_time_features_all_seasons_valid(sample_clean_df):
    assert set(sample_clean_df["season"].unique()).issubset(set(cleaning.SEASON_ORDER))


def test_validate_cleaned_dataset_passes_on_valid_data(sample_clean_df):
    n = 2000
    timestamps = pd.date_range("2023-08-04", periods=n, freq="4h")
    df = pd.DataFrame({"timestamp": timestamps, "record_number": range(n)})
    df = cleaning.add_time_features(df)
    cleaning.validate_cleaned_dataset(df, original_row_count=n)


def test_validate_cleaned_dataset_fails_on_row_count_mismatch():
    n = 2000
    timestamps = pd.date_range("2023-08-04", periods=n, freq="4h")
    df = pd.DataFrame({"timestamp": timestamps, "record_number": range(n)})
    df = cleaning.add_time_features(df)
    with pytest.raises(AssertionError):
        cleaning.validate_cleaned_dataset(df.iloc[:-1], original_row_count=n)


def test_validate_cleaned_dataset_fails_on_duplicate_record_number():
    n = 2000
    timestamps = pd.date_range("2023-08-04", periods=n, freq="4h")
    df = pd.DataFrame({"timestamp": timestamps, "record_number": [0] * n})
    df = cleaning.add_time_features(df)
    with pytest.raises(AssertionError):
        cleaning.validate_cleaned_dataset(df, original_row_count=n)
