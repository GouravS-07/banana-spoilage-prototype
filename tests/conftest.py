"""
Pytest configuration and fixtures.
Uses an isolated in-memory SQLite database with StaticPool for test execution.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.device import RegisteredDevice
from app.models.batch import Batch

# In-memory database with StaticPool ensures all connections share the same memory database
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function")
def db_session():
    """Provides a clean in-memory database session for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Pre-seed test device
    dev = RegisteredDevice(
        device_id="ESP32-TEST-UNIT",
        device_token="valid-test-token-xyz",
        description="Test Hardware Device",
        is_active=True
    )
    session.add(dev)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Provides FastAPI TestClient wired to the test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
