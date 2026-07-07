"""Data cleaning and feature engineering used by training and prediction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RAW_COLUMNS = [
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "weather_description",
    "date_time",
    "traffic_volume",
]

MODEL_FEATURES = [
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "moving_avg_24h",
    "moving_avg_168h",
]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Load the original CSV while keeping the literal holiday label `None`."""
    frame = pd.read_csv(path, keep_default_na=False)
    missing_columns = sorted(set(RAW_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {missing_columns}")
    frame["date_time"] = pd.to_datetime(frame["date_time"], errors="raise")
    return frame.sort_values("date_time").reset_index(drop=True)


def _mode_or_first(series: pd.Series):
    modes = series.mode(dropna=True)
    return modes.iloc[0] if len(modes) else series.iloc[0]


def aggregate_to_hourly(raw: pd.DataFrame) -> pd.DataFrame:
    """Create one record per timestamp from repeated weather descriptions."""
    clean = raw.drop_duplicates().copy()
    clean["holiday"] = clean["holiday"].replace({"None": "No Holiday", "": "No Holiday"})

    hourly = (
        clean.groupby("date_time", as_index=False)
        .agg(
            holiday=("holiday", _mode_or_first),
            temp=("temp", "mean"),
            rain_1h=("rain_1h", "mean"),
            snow_1h=("snow_1h", "mean"),
            clouds_all=("clouds_all", "mean"),
            weather_main=("weather_main", _mode_or_first),
            weather_description=("weather_description", lambda s: " | ".join(sorted(set(s)))),
            traffic_volume=("traffic_volume", "mean"),
        )
        .sort_values("date_time")
        .reset_index(drop=True)
    )
    return hourly


def make_regular_hourly(hourly: pd.DataFrame, interpolation_limit: int = 3) -> pd.DataFrame:
    """Reindex hourly and fill only short gaps of at most three hours.

    Long gaps remain missing and are excluded from model fitting. This avoids
    inventing long stretches of traffic history.
    """
    regular = hourly.set_index("date_time").asfreq("h")
    regular["was_missing_hour"] = regular["traffic_volume"].isna().astype(int)

    numeric = ["temp", "rain_1h", "snow_1h", "clouds_all", "traffic_volume"]
    regular[numeric] = regular[numeric].interpolate(
        method="time", limit=interpolation_limit, limit_area="inside"
    )
    categorical = ["holiday", "weather_main", "weather_description"]
    regular[categorical] = regular[categorical].ffill(limit=interpolation_limit)
    regular["holiday"] = regular["holiday"].fillna("No Holiday")
    return regular.reset_index()


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add calendar, lag and past-only rolling features."""
    result = frame.sort_values("date_time").copy()
    timestamp = pd.to_datetime(result["date_time"])
    result["hour"] = timestamp.dt.hour
    result["day_of_week"] = timestamp.dt.dayofweek
    result["month"] = timestamp.dt.month
    result["is_weekend"] = (result["day_of_week"] >= 5).astype(int)
    result["is_holiday"] = (~result["holiday"].isin(["No Holiday", "None", ""])).astype(int)

    target = result["traffic_volume"]
    result["lag_1h"] = target.shift(1)
    result["lag_24h"] = target.shift(24)
    result["lag_168h"] = target.shift(168)
    past_target = target.shift(1)
    result["moving_avg_24h"] = past_target.rolling(24, min_periods=12).mean()
    result["moving_avg_168h"] = past_target.rolling(168, min_periods=84).mean()
    return result


def prepare_dataset(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return raw, unique-hour and feature-engineered regular datasets."""
    raw = load_raw(path)
    hourly = aggregate_to_hourly(raw)
    regular = make_regular_hourly(hourly)
    featured = add_time_features(regular)
    return raw, hourly, featured


def model_rows(featured: pd.DataFrame) -> pd.DataFrame:
    """Return rows having a real/short-gap target and all model predictors."""
    needed = MODEL_FEATURES + ["traffic_volume", "date_time"]
    result = featured[needed].replace([np.inf, -np.inf], np.nan).dropna().copy()
    return result.sort_values("date_time").reset_index(drop=True)

