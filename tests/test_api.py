"""Integration tests covering CRUD, latest and date-range endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete

from src.api.database import Base, SessionLocal, engine, mongo_db
from src.api.main import app
from src.api.models import Location, TrafficRecord, WeatherCondition


PAYLOAD = {
    "date_time": "2018-10-01T00:00:00",
    "holiday": "No Holiday",
    "temp": 282.5,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 75,
    "weather_main": "Clouds",
    "weather_description": "broken clouds",
    "traffic_volume": 1000,
    "location_id": 1,
}


def reset_databases() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.execute(delete(TrafficRecord))
        session.execute(delete(WeatherCondition))
        session.execute(delete(Location))
        session.add(Location(id=1, station_code="ATR-301", road_name="I-94 Westbound", direction="Westbound", city="Minneapolis-St. Paul", state="Minnesota"))
        session.commit()
    mongo_db.traffic_records.delete_many({})


def exercise_crud(client: TestClient, prefix: str) -> None:
    created = client.post(f"/{prefix}/records", json=PAYLOAD)
    assert created.status_code == 201, created.text
    record = created.json()
    record_id = record["id"]

    fetched = client.get(f"/{prefix}/records/{record_id}")
    assert fetched.status_code == 200
    assert fetched.json()["traffic_volume"] == 1000

    ranged = client.get(f"/{prefix}/records", params={"start": "2018-10-01T00:00:00", "end": "2018-10-01T01:00:00"})
    assert ranged.status_code == 200
    assert len(ranged.json()) == 1

    latest = client.get(f"/{prefix}/records/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == record_id

    updated = client.put(f"/{prefix}/records/{record_id}", json={"traffic_volume": 1250})
    assert updated.status_code == 200
    assert updated.json()["traffic_volume"] == 1250

    deleted = client.delete(f"/{prefix}/records/{record_id}")
    assert deleted.status_code == 204
    assert client.get(f"/{prefix}/records/{record_id}").status_code == 404


def test_sql_and_mongo_endpoints() -> None:
    reset_databases()
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        exercise_crud(client, "sql")
        exercise_crud(client, "mongo")

