"""Relational ORM models for the normalized traffic schema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    road_name: Mapped[str] = mapped_column(String(120), nullable=False)
    direction: Mapped[str] = mapped_column(String(30), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    records: Mapped[list["TrafficRecord"]] = relationship(back_populates="location")


class WeatherCondition(Base):
    __tablename__ = "weather_conditions"
    __table_args__ = (UniqueConstraint("weather_main", "weather_description", name="uq_weather_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    weather_main: Mapped[str] = mapped_column(String(50), nullable=False)
    weather_description: Mapped[str] = mapped_column(String(255), nullable=False)
    records: Mapped[list["TrafficRecord"]] = relationship(back_populates="weather_condition")


class TrafficRecord(Base):
    __tablename__ = "traffic_records"
    __table_args__ = (UniqueConstraint("location_id", "date_time", name="uq_location_timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False, index=True)
    weather_condition_id: Mapped[int] = mapped_column(ForeignKey("weather_conditions.id"), nullable=False)
    date_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    holiday: Mapped[str] = mapped_column(String(80), nullable=False, default="No Holiday")
    temp: Mapped[float] = mapped_column(Float, nullable=False)
    rain_1h: Mapped[float] = mapped_column(Float, nullable=False)
    snow_1h: Mapped[float] = mapped_column(Float, nullable=False)
    clouds_all: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_volume: Mapped[int] = mapped_column(Integer, nullable=False)

    location: Mapped[Location] = relationship(back_populates="records")
    weather_condition: Mapped[WeatherCondition] = relationship(back_populates="records")


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    traffic_record_id: Mapped[int] = mapped_column(ForeignKey("traffic_records.id"), nullable=False, index=True)
    predicted_volume: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

