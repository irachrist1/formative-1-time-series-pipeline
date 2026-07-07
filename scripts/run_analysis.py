"""Generate Task 1 statistics, visualizations, experiments and trained model."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import joblib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import MODEL_FEATURES, model_rows, prepare_dataset


RAW_PATH = ROOT / "data/raw/Metro_Interstate_Traffic_Volume.csv"
PROCESSED_PATH = ROOT / "data/processed/metro_traffic_hourly.csv"
FIGURE_DIR = ROOT / "outputs/figures"
TABLE_DIR = ROOT / "outputs/tables"
MODEL_DIR = ROOT / "models"

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
    "blue": "#A3BEFA",
    "blue_dark": "#2E4780",
    "gold": "#FFE15B",
    "gold_dark": "#736422",
    "orange": "#F0986E",
    "orange_dark": "#804126",
    "olive": "#A3D576",
    "olive_dark": "#386411",
    "pink": "#F390CA",
    "pink_dark": "#8A3A6F",
}


def use_theme() -> None:
    sns.set_theme(
        style="whitegrid",
        rc={
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "text.color": TOKENS["ink"],
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": ["Aptos", "Inter", "DejaVu Sans", "Arial"],
        },
    )


def add_header(fig, ax, title: str, subtitle: str) -> None:
    ax.set_title("")
    fig.subplots_adjust(top=0.82)
    left = ax.get_position().x0
    fig.text(left, 0.97, title, ha="left", va="top", fontsize=14, fontweight="semibold", color=TOKENS["ink"])
    fig.text(left, 0.92, subtitle, ha="left", va="top", fontsize=9, color=TOKENS["muted"])
    sns.despine(ax=ax)


def save_figure(fig, name: str) -> None:
    fig.savefig(FIGURE_DIR / f"{name}.png", dpi=180, bbox_inches="tight", facecolor=TOKENS["surface"])
    fig.savefig(FIGURE_DIR / f"{name}.svg", bbox_inches="tight", facecolor=TOKENS["surface"])
    plt.close(fig)


def create_figures(hourly: pd.DataFrame, featured: pd.DataFrame) -> dict:
    findings = {}

    monthly = hourly.set_index("date_time")["traffic_volume"].resample("MS").mean().dropna()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    sns.lineplot(x=monthly.index, y=monthly.values, ax=ax, color=TOKENS["blue"], linewidth=1.4)
    ax.plot(monthly.index, monthly.rolling(12, min_periods=6).mean(), color=TOKENS["blue_dark"], linestyle="--", linewidth=1.2, label="12-month mean")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set(xlabel="Month", ylabel="Average vehicles per hour")
    ax.legend(frameon=False, loc="upper left")
    add_header(fig, ax, "Monthly traffic volume", "Hourly observations aggregated by month, October 2012 to September 2018")
    save_figure(fig, "q1_monthly_trend")
    first_year = monthly.loc[monthly.index < monthly.index.min() + pd.DateOffset(years=1)].mean()
    last_year = monthly.loc[monthly.index >= monthly.index.max() - pd.DateOffset(years=1)].mean()
    findings["q1"] = {"first_12_month_mean": round(first_year, 2), "last_12_month_mean": round(last_year, 2), "percent_change": round((last_year / first_year - 1) * 100, 2)}

    pattern = hourly.assign(hour=hourly.date_time.dt.hour, weekday=hourly.date_time.dt.day_name()).pivot_table(index="weekday", columns="hour", values="traffic_volume", aggfunc="mean")
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pattern = pattern.reindex(weekday_order)
    fig, ax = plt.subplots(figsize=(10, 4.7))
    cmap = sns.blend_palette([TOKENS["panel"], "#EAF1FE", TOKENS["blue"]], as_cmap=True)
    sns.heatmap(pattern, ax=ax, cmap=cmap, linewidths=0.35, linecolor=TOKENS["panel"], cbar_kws={"label": "Vehicles/hour"})
    ax.set(xlabel="Hour of day", ylabel="Day of week")
    add_header(fig, ax, "Traffic by hour and weekday", "Mean hourly volume; darker cells indicate busier periods")
    save_figure(fig, "q2_hour_weekday_heatmap")
    peak = pattern.stack().idxmax()
    findings["q2"] = {"peak_weekday": peak[0], "peak_hour": int(peak[1]), "peak_mean": round(float(pattern.stack().max()), 2)}

    weather = hourly.groupby("weather_main").agg(mean_traffic=("traffic_volume", "mean"), observations=("traffic_volume", "size")).query("observations >= 100").sort_values("mean_traffic")
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(weather.index, weather.mean_traffic, color=TOKENS["orange"], edgecolor=TOKENS["orange_dark"], linewidth=1)
    ax.bar_label(bars, fmt="%.0f", padding=4, fontsize=8)
    ax.set(xlabel="Average vehicles per hour", ylabel="Weather category")
    add_header(fig, ax, "Traffic volume under common weather conditions", "Categories with at least 100 hourly observations")
    save_figure(fig, "q3_weather_comparison")
    findings["q3"] = {"highest_weather": weather.mean_traffic.idxmax(), "highest_mean": round(weather.mean_traffic.max(), 2), "lowest_weather": weather.mean_traffic.idxmin(), "lowest_mean": round(weather.mean_traffic.min(), 2)}

    lag_columns = ["lag_1h", "lag_24h", "lag_168h"]
    lag_corr = featured[["traffic_volume"] + lag_columns].corr()["traffic_volume"].drop("traffic_volume").rename("correlation")
    lag_corr.index = ["Previous hour", "Same hour yesterday", "Same hour last week"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bars = ax.barh(lag_corr.sort_values().index, lag_corr.sort_values().values, color=TOKENS["gold"], edgecolor=TOKENS["gold_dark"], linewidth=1)
    ax.bar_label(bars, fmt="%.3f", padding=4, fontsize=9)
    ax.set(xlim=(0, 1), xlabel="Pearson correlation", ylabel="Lag feature")
    add_header(fig, ax, "Current traffic is related to earlier traffic", "Correlation computed on timestamp-aligned hourly records")
    save_figure(fig, "q4_lag_correlations")
    findings["q4"] = {k: round(float(v), 4) for k, v in lag_corr.items()}

    window = featured[(featured.date_time >= "2018-08-01") & (featured.date_time < "2018-09-01")].copy()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(window.date_time, window.traffic_volume, color="#C5CAD3", linewidth=0.8, label="Hourly traffic")
    ax.plot(window.date_time, window.moving_avg_24h, color=TOKENS["blue"], linewidth=1.2, label="24-hour moving average")
    ax.plot(window.date_time, window.moving_avg_168h, color=TOKENS["orange_dark"], linestyle="--", linewidth=1.3, label="168-hour moving average")
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set(xlabel="Date", ylabel="Vehicles per hour")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    add_header(fig, ax, "Moving averages reveal daily and weekly traffic levels", "August 2018; rolling values use only earlier observations")
    save_figure(fig, "q5_moving_averages")
    findings["q5"] = {"hourly_std": round(window.traffic_volume.std(), 2), "ma24_std": round(window.moving_avg_24h.std(), 2), "ma168_std": round(window.moving_avg_168h.std(), 2)}

    temp = hourly.assign(temp_c=hourly.temp - 273.15)
    temp_bins = pd.cut(temp.temp_c, bins=[-40, 0, 10, 20, 30, 45], include_lowest=True)
    temp_summary = temp.groupby(temp_bins, observed=True).agg(mean_traffic=("traffic_volume", "mean"), observations=("traffic_volume", "size")).reset_index()
    temp_summary["temperature_range"] = temp_summary.temp_c.astype(str)
    fig, ax = plt.subplots(figsize=(9, 4.7))
    bars = ax.bar(temp_summary.temperature_range, temp_summary.mean_traffic, color=TOKENS["olive"], edgecolor=TOKENS["olive_dark"], linewidth=1)
    ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=8)
    ax.set(xlabel="Temperature range (degrees Celsius)", ylabel="Average vehicles per hour")
    add_header(fig, ax, "Traffic volume across temperature ranges", "All available hours grouped into practical temperature bands")
    save_figure(fig, "q6_temperature_bands")
    findings["q6"] = {row.temperature_range: {"mean": round(row.mean_traffic, 2), "n": int(row.observations)} for row in temp_summary.itertuples()}

    fig, ax = plt.subplots(figsize=(8.5, 4.7))
    sns.histplot(hourly, x="traffic_volume", bins=40, ax=ax, color=TOKENS["pink"], edgecolor=TOKENS["pink_dark"], linewidth=0.7)
    ax.axvline(hourly.traffic_volume.median(), color=TOKENS["ink"], linestyle=":", linewidth=1, label=f"Median: {hourly.traffic_volume.median():.0f}")
    ax.set(xlabel="Vehicles per hour", ylabel="Number of hourly records")
    ax.legend(frameon=False)
    add_header(fig, ax, "Distribution of hourly traffic volume", f"Unique observed hours, n={len(hourly):,}")
    save_figure(fig, "traffic_distribution")
    return findings


def train_experiments(featured: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    data = model_rows(featured)
    train_end = int(len(data) * 0.70)
    validation_end = int(len(data) * 0.85)
    train = data.iloc[:train_end]
    validation = data.iloc[train_end:validation_end]
    test = data.iloc[validation_end:]

    experiments = [
        {"experiment": "RF-1", "n_estimators": 60, "max_depth": 12, "min_samples_leaf": 4},
        {"experiment": "RF-2", "n_estimators": 100, "max_depth": 18, "min_samples_leaf": 2},
        {"experiment": "RF-3", "n_estimators": 140, "max_depth": None, "min_samples_leaf": 2},
    ]
    rows = []
    trained = {}
    for params in experiments:
        model = RandomForestRegressor(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            max_features=0.8,
            n_jobs=-1,
            random_state=42,
        )
        model.fit(train[MODEL_FEATURES], train["traffic_volume"])
        pred = model.predict(validation[MODEL_FEATURES])
        rows.append(
            {
                **params,
                "validation_mae": mean_absolute_error(validation.traffic_volume, pred),
                "validation_rmse": mean_squared_error(validation.traffic_volume, pred) ** 0.5,
                "validation_r2": r2_score(validation.traffic_volume, pred),
            }
        )
        trained[params["experiment"]] = model

    results = pd.DataFrame(rows).sort_values("validation_rmse").reset_index(drop=True)
    best_name = results.iloc[0].experiment
    best_params = next(item for item in experiments if item["experiment"] == best_name)
    final_train = data.iloc[:validation_end]
    best_model = RandomForestRegressor(
        n_estimators=best_params["n_estimators"],
        max_depth=best_params["max_depth"],
        min_samples_leaf=best_params["min_samples_leaf"],
        max_features=0.8,
        n_jobs=-1,
        random_state=42,
    )
    best_model.fit(final_train[MODEL_FEATURES], final_train.traffic_volume)
    test_pred = best_model.predict(test[MODEL_FEATURES])
    metrics = {
        "best_experiment": best_name,
        "test_mae": float(mean_absolute_error(test.traffic_volume, test_pred)),
        "test_rmse": float(mean_squared_error(test.traffic_volume, test_pred) ** 0.5),
        "test_r2": float(r2_score(test.traffic_volume, test_pred)),
        "train_rows": int(len(final_train)),
        "test_rows": int(len(test)),
        "train_end": str(final_train.date_time.max()),
        "test_start": str(test.date_time.min()),
        "test_end": str(test.date_time.max()),
    }
    artifact = {
        "model": best_model,
        "features": MODEL_FEATURES,
        "metrics": metrics,
        "last_timestamp": str(featured.date_time.max()),
    }
    joblib.dump(artifact, MODEL_DIR / "traffic_forecaster.joblib", compress=3)

    predictions = test[["date_time", "traffic_volume"]].copy()
    predictions["prediction"] = test_pred
    predictions.to_csv(TABLE_DIR / "test_predictions.csv", index=False)

    sample = predictions.tail(24 * 14)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(sample.date_time, sample.traffic_volume, color=TOKENS["blue_dark"], linewidth=1.2, label="Actual")
    ax.plot(sample.date_time, sample.prediction, color=TOKENS["orange"], linestyle="--", linewidth=1.1, label="Predicted")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set(xlabel="Date", ylabel="Vehicles per hour")
    ax.legend(frameon=False, loc="upper left")
    add_header(fig, ax, "Forecast performance on the final test period", "Actual and predicted hourly traffic for the last 14 days")
    save_figure(fig, "model_test_predictions")

    importance = pd.DataFrame({"feature": MODEL_FEATURES, "importance": best_model.feature_importances_}).sort_values("importance").tail(10)
    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.barh(importance.feature, importance.importance, color=TOKENS["gold"], edgecolor=TOKENS["gold_dark"], linewidth=1)
    ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set(xlabel="Random forest feature importance", ylabel="Feature")
    add_header(fig, ax, "Most influential forecasting features", f"Selected model: {best_name}")
    save_figure(fig, "model_feature_importance")
    return results, metrics


def main() -> None:
    for directory in [PROCESSED_PATH.parent, FIGURE_DIR, TABLE_DIR, MODEL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    use_theme()
    raw, hourly, featured = prepare_dataset(RAW_PATH)
    featured.to_csv(PROCESSED_PATH, index=False)

    summary = pd.DataFrame(
        {
            "value": {
                "raw_rows": len(raw),
                "raw_columns": raw.shape[1],
                "start": raw.date_time.min(),
                "end": raw.date_time.max(),
                "full_duplicate_rows": int(raw.duplicated().sum()),
                "repeated_timestamp_rows": int(raw.date_time.duplicated().sum()),
                "unique_observed_hours": len(hourly),
                "expected_hours": len(featured),
                "missing_hours_before_short_interpolation": int(featured.was_missing_hour.sum()),
                "remaining_missing_targets": int(featured.traffic_volume.isna().sum()),
            }
        }
    )
    summary.to_csv(TABLE_DIR / "data_quality_summary.csv")
    hourly.describe(include="all").transpose().to_csv(TABLE_DIR / "descriptive_statistics.csv")
    raw.isna().sum().rename("pandas_null_count").to_csv(TABLE_DIR / "raw_missing_values.csv")

    findings = create_figures(hourly, featured)
    experiments, metrics = train_experiments(featured)
    experiments.to_csv(TABLE_DIR / "model_experiments.csv", index=False)
    (TABLE_DIR / "analytical_findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    (TABLE_DIR / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(summary.to_string())
    print("\nModel experiments:\n", experiments.to_string(index=False))
    print("\nTest metrics:\n", json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
