"""Database connection engine and session factory."""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.core.config import settings

import logging

logger = logging.getLogger("uvicorn.error")

active_db_url = settings.DATABASE_URL
connect_args = {}

if active_db_url.startswith("mysql"):
    # Normalize mysql:// to mysql+pymysql://
    if active_db_url.startswith("mysql://"):
        active_db_url = active_db_url.replace("mysql://", "mysql+pymysql://", 1)
    try:
        test_engine = create_engine(
            active_db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
        )
        with test_engine.connect():
            pass
        engine = test_engine
        logger.info("Successfully connected to MySQL database cluster.")
    except Exception as exc:
        logger.warning(
            f"MySQL at {active_db_url.split('@')[-1]} not reachable ({exc}). "
            "Using persistent fallback SQLite store at ./data/app.db"
        )
        active_db_url = "sqlite:///./data/app.db"
        os.makedirs("./data", exist_ok=True)
        connect_args = {"check_same_thread": False}
        engine = create_engine(active_db_url, connect_args=connect_args, pool_pre_ping=True)
elif active_db_url.startswith("postgresql"):
    try:
        test_engine = create_engine(
            active_db_url,
            connect_args={},
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20,
        )
        with test_engine.connect():
            pass
        engine = test_engine
        logger.info("Successfully connected to PostgreSQL database cluster.")
    except Exception as exc:
        logger.warning(
            f"PostgreSQL at {active_db_url.split('@')[-1]} not reachable ({exc}). "
            "Using persistent fallback SQLite store at ./data/app.db"
        )
        active_db_url = "sqlite:///./data/app.db"
        os.makedirs("./data", exist_ok=True)
        connect_args = {"check_same_thread": False}
        engine = create_engine(active_db_url, connect_args=connect_args, pool_pre_ping=True)
elif active_db_url.startswith("sqlite"):
    db_path = active_db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    connect_args = {"check_same_thread": False}
    engine = create_engine(active_db_url, connect_args=connect_args, pool_pre_ping=True)
else:
    engine = create_engine(active_db_url, pool_pre_ping=True, pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database_engine_name() -> str:
    """Return human-readable database dialect/engine currently active."""
    dialect = engine.dialect.name.lower()
    if "postgres" in dialect:
        return "PostgreSQL"
    elif "mysql" in dialect:
        return "MySQL"
    elif "sqlite" in dialect:
        return "SQLite"
    return dialect.capitalize()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
