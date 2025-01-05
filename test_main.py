"""
This module contains tests for the FastAPI application endpoints.
"""

from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app

client = TestClient(app)

def test_version():
    """Test the /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == "0.0.1"  # Check if the version matches

def test_temperature():
    """Test the /temperature endpoint."""
    response = client.get("/temperature")
    assert response.status_code in [200, 404]  # Check for valid responses
    if response.status_code == 200:
        assert "message" in response.json()  # Ensure the message key is present
