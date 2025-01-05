"""
This module contains tests for the FastAPI application endpoints.
"""

from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app
import pytest

client = TestClient(app)

def test_version():
    """Test the /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == "0.0.1"  # Check if the version matches


def test_temperature_success():
    """Test the /temperature endpoint with successful data retrieval."""
    # Mock the external API response
    mock_response = [
        {
            "sensors": [
                {
                    "title": "Temperatur",
                    "lastMeasurement": {"value": "20"}
                }
            ]
        }
    ]
    
    # Use pytest's monkeypatch to mock the requests.get call
    def mock_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data):
                self.json_data = json_data
            
            def json(self):
                return self.json_data
        
        return MockResponse(mock_response)
    
    # Apply the mock
    import requests
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_get)
    
    response = client.get("/temperature")
    assert response.status_code == 200
    assert response.json() == {"temperature": 20, "status": "Good"}

def test_temperature_no_data():
    """Test the /temperature endpoint when no temperature data is found."""
    # Mock the external API response with no temperature data
    mock_response = [
        {
            "sensors": [
                {
                    "title": "Humidity",
                    "lastMeasurement": {"value": "50"}
                }
            ]
        }
    ]
    
    def mock_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data):
                self.json_data = json_data
            
            def json(self):
                return self.json_data
        
        return MockResponse(mock_response)
    
    import requests
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_get)
    
    response = client.get("/temperature")
    assert response.status_code == 404
    assert response.json() == {"detail": "No Temp data found"}

def test_temperature_api_error():
    """Test the /temperature endpoint when the external API fails."""
    def mock_get(*args, **kwargs):
        raise requests.RequestException("API Error")
    
    import requests
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_get)
    
    response = client.get("/temperature")
    assert response.status_code == 500
    assert "API Error" in response.json()["detail"]