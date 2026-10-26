"""Pytest configuration and test database isolation fixtures."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.session import get_db
from backend.app.models import Base, User, UserRole
from backend.app.core.security import get_password_hash

TEST_DB_PATH = "./data/test.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure clean test database, create tables, and seed initial test administrator."""
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    Base.metadata.create_all(bind=engine_test)

    # Seed initial test administrator
    db = TestingSessionLocal()
    admin = User(
        email="admin@institution.edu",
        full_name="System Administrator",
        hashed_password=get_password_hash("AdminSecr3t!2026"),
        role=UserRole.ADMIN,
        is_active=True,
        institution="System Administration",
        department="IT / Research Governance",
    )
    db.add(admin)
    db.commit()
    db.close()

    yield

    # Clean up test DB file at end of session
    try:
        engine_test.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except OSError:
        pass


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Fixture providing TestClient with dependency-overridden test database session."""

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
