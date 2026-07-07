"""CRUD and time-series endpoints for SQL and MongoDB."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pymongo.errors import DuplicateKeyError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .database import Base, SessionLocal, engine, get_sql_session, mongo_db
from .models import Location, TrafficRecord, WeatherCondition
from .schemas import MongoRecordResponse, SQLRecordResponse, TrafficRecordInput, TrafficRecordUpdate

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.get(Location, 1) is None:
            session.add(Location(id=1, station_code="ATR-301", road_name="I-94 Westbound", direction="Westbound", city="Minneapolis-St. Paul", state="Minnesota"))
            session.commit()
    yield


app = FastAPI(
    title="Metro Traffic Time-Series API",
    description="CRUD, date-range and latest-record operations for SQL and MongoDB.",
    version="1.0.0",
    lifespan=lifespan,
)


def sql_to_response(record: TrafficRecord) -> dict:
    return {
        "id": record.id,
        "date_time": record.date_time,
        "holiday": record.holiday,
        "temp": record.temp,
        "rain_1h": record.rain_1h,
        "snow_1h": record.snow_1h,
        "clouds_all": record.clouds_all,
        "weather_main": record.weather_condition.weather_main,
        "weather_description": record.weather_condition.weather_description,
        "traffic_volume": record.traffic_volume,
        "location_id": record.location_id,
    }


def mongo_to_response(document: dict) -> dict:
    result = dict(document)
    result["id"] = str(result.pop("_id"))
    weather = result.pop("weather")
    result.update(weather)
    return result


def get_or_create_weather(session: Session, main: str, description: str) -> WeatherCondition:
    weather = session.scalar(select(WeatherCondition).where(WeatherCondition.weather_main == main, WeatherCondition.weather_description == description))
    if weather is None:
        weather = WeatherCondition(weather_main=main, weather_description=description)
        session.add(weather)
        session.flush()
    return weather


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sql/records", response_model=SQLRecordResponse, status_code=status.HTTP_201_CREATED)
def create_sql_record(payload: TrafficRecordInput, session: Session = Depends(get_sql_session)):
    if session.get(Location, payload.location_id) is None:
        raise HTTPException(404, "Location not found")
    weather = get_or_create_weather(session, payload.weather_main, payload.weather_description)
    record = TrafficRecord(
        location_id=payload.location_id,
        weather_condition_id=weather.id,
        date_time=payload.date_time,
        holiday=payload.holiday,
        temp=payload.temp,
        rain_1h=payload.rain_1h,
        snow_1h=payload.snow_1h,
        clouds_all=payload.clouds_all,
        traffic_volume=payload.traffic_volume,
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "A SQL record already exists for this location and timestamp")
    session.refresh(record)
    return sql_to_response(record)


@app.get("/sql/records/latest", response_model=SQLRecordResponse)
def latest_sql_record(session: Session = Depends(get_sql_session)):
    record = session.scalar(select(TrafficRecord).options(joinedload(TrafficRecord.weather_condition)).order_by(TrafficRecord.date_time.desc()).limit(1))
    if record is None:
        raise HTTPException(404, "No SQL records found")
    return sql_to_response(record)


@app.get("/sql/records", response_model=list[SQLRecordResponse])
def list_sql_records(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_sql_session),
):
    query = select(TrafficRecord).options(joinedload(TrafficRecord.weather_condition)).order_by(TrafficRecord.date_time)
    if start:
        query = query.where(TrafficRecord.date_time >= start)
    if end:
        query = query.where(TrafficRecord.date_time <= end)
    return [sql_to_response(item) for item in session.scalars(query.limit(limit)).all()]


@app.get("/sql/records/{record_id}", response_model=SQLRecordResponse)
def get_sql_record(record_id: int, session: Session = Depends(get_sql_session)):
    record = session.scalar(select(TrafficRecord).options(joinedload(TrafficRecord.weather_condition)).where(TrafficRecord.id == record_id))
    if record is None:
        raise HTTPException(404, "SQL record not found")
    return sql_to_response(record)


@app.put("/sql/records/{record_id}", response_model=SQLRecordResponse)
def update_sql_record(record_id: int, payload: TrafficRecordUpdate, session: Session = Depends(get_sql_session)):
    record = session.scalar(select(TrafficRecord).options(joinedload(TrafficRecord.weather_condition)).where(TrafficRecord.id == record_id))
    if record is None:
        raise HTTPException(404, "SQL record not found")
    updates = payload.model_dump(exclude_unset=True)
    weather_main = updates.pop("weather_main", None)
    weather_description = updates.pop("weather_description", None)
    if weather_main is not None or weather_description is not None:
        weather = get_or_create_weather(session, weather_main or record.weather_condition.weather_main, weather_description or record.weather_condition.weather_description)
        record.weather_condition_id = weather.id
    for key, value in updates.items():
        setattr(record, key, value)
    session.commit()
    session.refresh(record)
    return sql_to_response(record)


@app.delete("/sql/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sql_record(record_id: int, session: Session = Depends(get_sql_session)):
    record = session.get(TrafficRecord, record_id)
    if record is None:
        raise HTTPException(404, "SQL record not found")
    session.delete(record)
    session.commit()


@app.post("/mongo/records", response_model=MongoRecordResponse, status_code=status.HTTP_201_CREATED)
def create_mongo_record(payload: TrafficRecordInput):
    data = payload.model_dump()
    document = {
        "date_time": data.pop("date_time"),
        "location_id": data.pop("location_id"),
        "holiday": data.pop("holiday"),
        "traffic_volume": data.pop("traffic_volume"),
        "temp": data.pop("temp"),
        "rain_1h": data.pop("rain_1h"),
        "snow_1h": data.pop("snow_1h"),
        "clouds_all": data.pop("clouds_all"),
        "weather": {"weather_main": data.pop("weather_main"), "weather_description": data.pop("weather_description")},
    }
    try:
        inserted = mongo_db.traffic_records.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(409, "A MongoDB record already exists for this timestamp")
    return mongo_to_response(mongo_db.traffic_records.find_one({"_id": inserted.inserted_id}))


@app.get("/mongo/records/latest", response_model=MongoRecordResponse)
def latest_mongo_record():
    document = mongo_db.traffic_records.find_one(sort=[("date_time", -1)])
    if document is None:
        raise HTTPException(404, "No MongoDB records found")
    return mongo_to_response(document)


@app.get("/mongo/records", response_model=list[MongoRecordResponse])
def list_mongo_records(start: Optional[datetime] = None, end: Optional[datetime] = None, limit: int = Query(100, ge=1, le=1000)):
    query = {}
    if start or end:
        query["date_time"] = {}
        if start:
            query["date_time"]["$gte"] = start
        if end:
            query["date_time"]["$lte"] = end
    cursor = mongo_db.traffic_records.find(query).sort("date_time", 1).limit(limit)
    return [mongo_to_response(item) for item in cursor]


def valid_object_id(record_id: str) -> ObjectId:
    if not ObjectId.is_valid(record_id):
        raise HTTPException(422, "Invalid MongoDB record id")
    return ObjectId(record_id)


@app.get("/mongo/records/{record_id}", response_model=MongoRecordResponse)
def get_mongo_record(record_id: str):
    document = mongo_db.traffic_records.find_one({"_id": valid_object_id(record_id)})
    if document is None:
        raise HTTPException(404, "MongoDB record not found")
    return mongo_to_response(document)


@app.put("/mongo/records/{record_id}", response_model=MongoRecordResponse)
def update_mongo_record(record_id: str, payload: TrafficRecordUpdate):
    updates = payload.model_dump(exclude_unset=True)
    mongo_updates = {}
    for key, value in updates.items():
        if key in {"weather_main", "weather_description"}:
            mongo_updates[f"weather.{key}"] = value
        else:
            mongo_updates[key] = value
    result = mongo_db.traffic_records.update_one({"_id": valid_object_id(record_id)}, {"$set": mongo_updates})
    if result.matched_count == 0:
        raise HTTPException(404, "MongoDB record not found")
    return mongo_to_response(mongo_db.traffic_records.find_one({"_id": ObjectId(record_id)}))


@app.delete("/mongo/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mongo_record(record_id: str):
    result = mongo_db.traffic_records.delete_one({"_id": valid_object_id(record_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "MongoDB record not found")
