"""Fetch API records, apply training-time features and make one prediction."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import joblib
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features import add_time_features


def predict(api_url: str, database: str = "sql") -> dict:
    latest_response = requests.get(f"{api_url}/{database}/records/latest", timeout=10)
    latest_response.raise_for_status()
    latest = latest_response.json()
    latest_time = pd.Timestamp(latest["date_time"])
    start_time = latest_time - timedelta(days=14)

    history_response = requests.get(
        f"{api_url}/{database}/records",
        params={"start": start_time.isoformat(), "end": latest_time.isoformat(), "limit": 1000},
        timeout=10,
    )
    history_response.raise_for_status()
    history = pd.DataFrame(history_response.json())
    if len(history) < 169:
        raise RuntimeError("At least 169 hourly API records are required for lag and moving-average features")
    history["date_time"] = pd.to_datetime(history["date_time"])
    featured = add_time_features(history)

    artifact = joblib.load(ROOT / "models/traffic_forecaster.joblib")
    row = featured.iloc[-1]
    features = artifact["features"]
    if row[features].isna().any():
        missing = row[features][row[features].isna()].index.tolist()
        raise RuntimeError(f"Latest API record cannot be predicted because features are missing: {missing}")
    prediction = float(artifact["model"].predict(pd.DataFrame([row[features].to_dict()]))[0])
    result = {
        "database": database,
        "record_id": str(latest["id"]),
        "date_time": latest["date_time"],
        "actual_traffic_volume": latest["traffic_volume"],
        "predicted_traffic_volume": round(prediction, 2),
        "absolute_error": round(abs(prediction - latest["traffic_volume"]), 2),
        "model": artifact["metrics"]["best_experiment"],
        "history_records_used": len(history),
    }
    output = ROOT / "outputs/tables/prediction_api_result.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--database", choices=["sql", "mongo"], default="sql")
    args = parser.parse_args()
    print(json.dumps(predict(args.api_url, args.database), indent=2))

