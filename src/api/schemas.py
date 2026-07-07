"""Request and response models shared by SQL and MongoDB routes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrafficRecordInput(BaseModel):
    date_time: datetime
    holiday: str = "No Holiday"
    temp: float = Field(ge=180, le=340)
    rain_1h: float = Field(ge=0)
    snow_1h: float = Field(ge=0)
    clouds_all: int = Field(ge=0, le=100)
    weather_main: str = Field(min_length=1, max_length=50)
    weather_description: str = Field(min_length=1, max_length=255)
    traffic_volume: int = Field(ge=0)
    location_id: int = Field(default=1, ge=1)

    @field_validator("holiday")
    @classmethod
    def normalize_holiday(cls, value: str) -> str:
        return "No Holiday" if value in {"", "None"} else value


class TrafficRecordUpdate(BaseModel):
    holiday: Optional[str] = None
    temp: Optional[float] = Field(default=None, ge=180, le=340)
    rain_1h: Optional[float] = Field(default=None, ge=0)
    snow_1h: Optional[float] = Field(default=None, ge=0)
    clouds_all: Optional[int] = Field(default=None, ge=0, le=100)
    weather_main: Optional[str] = None
    weather_description: Optional[str] = None
    traffic_volume: Optional[int] = Field(default=None, ge=0)


class SQLRecordResponse(TrafficRecordInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class MongoRecordResponse(TrafficRecordInput):
    id: str
