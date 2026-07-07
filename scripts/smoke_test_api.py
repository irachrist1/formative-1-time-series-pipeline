"""Exercise live CRUD, latest and date-range routes for both databases."""

from __future__ import annotations

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
PAYLOAD = {
    "date_time": "2018-10-02T00:00:00",
    "holiday": "No Holiday",
    "temp": 283.0,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 50,
    "weather_main": "Clouds",
    "weather_description": "scattered clouds",
    "traffic_volume": 1200,
    "location_id": 1,
}


def run_for(database: str) -> dict:
    created = requests.post(f"{BASE_URL}/{database}/records", json=PAYLOAD, timeout=10)
    created.raise_for_status()
    record_id = created.json()["id"]

    read = requests.get(f"{BASE_URL}/{database}/records/{record_id}", timeout=10)
    ranged = requests.get(
        f"{BASE_URL}/{database}/records",
        params={"start": "2018-10-02T00:00:00", "end": "2018-10-02T01:00:00"},
        timeout=10,
    )
    latest = requests.get(f"{BASE_URL}/{database}/records/latest", timeout=10)
    updated = requests.put(f"{BASE_URL}/{database}/records/{record_id}", json={"traffic_volume": 1300}, timeout=10)
    deleted = requests.delete(f"{BASE_URL}/{database}/records/{record_id}", timeout=10)
    for response in [read, ranged, latest, updated, deleted]:
        response.raise_for_status()
    return {
        "POST": created.status_code,
        "GET": read.status_code,
        "DATE_RANGE": {"status": ranged.status_code, "rows": len(ranged.json())},
        "LATEST": {"status": latest.status_code, "id_matches": latest.json()["id"] == record_id},
        "PUT": {"status": updated.status_code, "traffic_volume": updated.json()["traffic_volume"]},
        "DELETE": deleted.status_code,
    }


if __name__ == "__main__":
    result = {database: run_for(database) for database in ["sql", "mongo"]}
    output = ROOT / "outputs/tables/live_api_smoke_test.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

