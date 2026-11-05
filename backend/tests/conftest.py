import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def override_db():
        with sessions() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    # No lifespan here: tests use only the isolated in-memory database.
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        yield test_client
    finally:
        test_client.close()
    engine.dispose()


@pytest.fixture
def profile_data():
    return {
        "name": "Sam",
        "study_area": "Data Science",
        "gpa": 3.5,
        "annual_budget_eur": 25000,
        "countries": [],
        "goals": "Explore AI research",
    }
