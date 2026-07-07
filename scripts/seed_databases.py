"""Seed the configured SQL and MongoDB databases with recent hourly records."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.database import Base, SessionLocal, engine, mongo_db
from src.api.models import Location, TrafficRecord, WeatherCondition


def seed(limit: int = 1000) -> dict:
    data = pd.read_csv(ROOT / "data/processed/metro_traffic_hourly.csv", parse_dates=["date_time"])
    data = data.dropna(subset=["traffic_volume", "temp", "weather_main"]).tail(limit)
    Base.metadata.create_all(engine)

    inserted_sql = 0
    with SessionLocal() as session:
        if session.get(Location, 1) is None:
            session.add(Location(id=1, station_code="ATR-301", road_name="I-94 Westbound", direction="Westbound", city="Minneapolis-St. Paul", state="Minnesota"))
            session.flush()
        weather_cache = {}
        for row in data.itertuples():
            existing = session.scalar(select(TrafficRecord.id).where(TrafficRecord.location_id == 1, TrafficRecord.date_time == row.date_time.to_pydatetime()))
            if existing:
                continue
            key = (str(row.weather_main), str(row.weather_description))
            weather = weather_cache.get(key)
            if weather is None:
                weather = session.scalar(select(WeatherCondition).where(WeatherCondition.weather_main == key[0], WeatherCondition.weather_description == key[1]))
                if weather is None:
                    weather = WeatherCondition(weather_main=key[0], weather_description=key[1])
                    session.add(weather)
                    session.flush()
                weather_cache[key] = weather
            session.add(TrafficRecord(
                location_id=1,
                weather_condition_id=weather.id,
                date_time=row.date_time.to_pydatetime(),
                holiday=str(row.holiday),
                temp=float(row.temp),
                rain_1h=float(row.rain_1h),
                snow_1h=float(row.snow_1h),
                clouds_all=int(row.clouds_all),
                traffic_volume=int(round(row.traffic_volume)),
            ))
            inserted_sql += 1
        session.commit()

    documents = []
    for row in data.itertuples():
        documents.append({
            "date_time": row.date_time.to_pydatetime(),
            "location_id": 1,
            "holiday": str(row.holiday),
            "temp": float(row.temp),
            "rain_1h": float(row.rain_1h),
            "snow_1h": float(row.snow_1h),
            "clouds_all": int(row.clouds_all),
            "traffic_volume": int(round(row.traffic_volume)),
            "weather": {"weather_main": str(row.weather_main), "weather_description": str(row.weather_description)},
        })
    inserted_mongo = 0
    for document in documents:
        result = mongo_db.traffic_records.update_one({"date_time": document["date_time"]}, {"$set": document}, upsert=True)
        inserted_mongo += int(result.upserted_id is not None)
    return {"sql_inserted": inserted_sql, "mongo_inserted": inserted_mongo, "source_rows": len(data)}


if __name__ == "__main__":
    print(seed())

