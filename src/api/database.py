"""SQL and MongoDB connections with local test-friendly defaults."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE = f"sqlite:///{ROOT / 'data/traffic_api.db'}"
SQL_DATABASE_URL = os.getenv("SQL_DATABASE_URL", DEFAULT_SQLITE)

connect_args = {"check_same_thread": False} if SQL_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQL_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_mongo_database():
    """Connect to MongoDB, or use mongomock when MONGO_MOCK=true."""
    use_mock = os.getenv("MONGO_MOCK", "true").lower() == "true"
    if use_mock:
        import mongomock

        client = mongomock.MongoClient()
    else:
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
    database = client[os.getenv("MONGO_DATABASE", "traffic_pipeline")]
    database.traffic_records.create_index([("date_time", ASCENDING)], unique=True)
    return database


mongo_db = get_mongo_database()


def get_sql_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

