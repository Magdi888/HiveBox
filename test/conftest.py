import pytest
from fastapi.testclient import TestClient
from app.api import app

@pytest.fixture
def client():
    """Fixture to provide a FastAPI test client."""
    return TestClient(app)
