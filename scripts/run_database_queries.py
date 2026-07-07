"""Execute three representative queries against both database implementations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.seed_databases import seed
from src.api.database import SessionLocal, mongo_db
from src.api.models import TrafficRecord, WeatherCondition


def serialize(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def main() -> None:
    seed(1000)
    results = {"sql": {}, "mongodb": {}}
    with SessionLocal() as session:
        latest = session.execute(
            select(TrafficRecord.date_time, TrafficRecord.traffic_volume, WeatherCondition.weather_main)
            .join(WeatherCondition)
            .order_by(TrafficRecord.date_time.desc())
            .limit(1)
        ).one()
        results["sql"]["latest_record"] = dict(zip(["date_time", "traffic_volume", "weather_main"], map(serialize, latest)))

        ranged = session.execute(
            select(TrafficRecord.date_time, TrafficRecord.traffic_volume)
            .where(TrafficRecord.date_time.between("2018-09-01", "2018-09-07 23:59:59"))
            .order_by(TrafficRecord.date_time)
        ).all()
        results["sql"]["date_range"] = {
            "row_count": len(ranged),
            "first_three": [{"date_time": serialize(row.date_time), "traffic_volume": row.traffic_volume} for row in ranged[:3]],
        }

        weather = session.execute(
            select(WeatherCondition.weather_main, func.round(func.avg(TrafficRecord.traffic_volume), 2), func.count())
            .join(TrafficRecord)
            .group_by(WeatherCondition.weather_main)
            .order_by(func.avg(TrafficRecord.traffic_volume).desc())
        ).all()
        results["sql"]["average_by_weather"] = [
            {"weather_main": row[0], "average_traffic": float(row[1]), "records": row[2]} for row in weather
        ]

    latest_doc = mongo_db.traffic_records.find_one(sort=[("date_time", -1)])
    results["mongodb"]["latest_record"] = {
        "date_time": serialize(latest_doc["date_time"]),
        "traffic_volume": latest_doc["traffic_volume"],
        "weather_main": latest_doc["weather"]["weather_main"],
    }
    ranged_docs = list(
        mongo_db.traffic_records.find(
            {"date_time": {"$gte": __import__("datetime").datetime(2018, 9, 1), "$lte": __import__("datetime").datetime(2018, 9, 7, 23, 59, 59)}}
        ).sort("date_time", 1)
    )
    results["mongodb"]["date_range"] = {
        "row_count": len(ranged_docs),
        "first_three": [{"date_time": serialize(doc["date_time"]), "traffic_volume": doc["traffic_volume"]} for doc in ranged_docs[:3]],
    }
    weather_docs = list(mongo_db.traffic_records.aggregate([
        {"$group": {"_id": "$weather.weather_main", "average_traffic": {"$avg": "$traffic_volume"}, "records": {"$sum": 1}}},
        {"$sort": {"average_traffic": -1}},
    ]))
    results["mongodb"]["average_by_weather"] = [
        {"weather_main": doc["_id"], "average_traffic": round(doc["average_traffic"], 2), "records": doc["records"]} for doc in weather_docs
    ]

    output = ROOT / "outputs/tables/database_query_results.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

