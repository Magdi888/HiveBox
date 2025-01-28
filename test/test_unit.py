
"""Tests for the application's unit tests."""
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.api import app
from app.services import (calculate_average_temperature,
                          fetch_temperature_from_api)
from app.storage import store_temperature_in_minio

# Initialize the FastAPI test client
client = TestClient(app)

def test_fetch_temperature_from_api_success():
    """Test fetching temperature data from the OpenSenseMap API."""
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

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        result = fetch_temperature_from_api()
        assert result == mock_response

def test_calculate_average_temperature():
    """Test calculating the average temperature."""
    mock_response = [
        {
            "sensors": [
                {
                    "title": "Temperatur",
                    "lastMeasurement": {"value": "20"}
                },
                {
                    "title": "Temperatur",
                    "lastMeasurement": {"value": "30"}
                }
            ]
        }
    ]

    result = calculate_average_temperature(mock_response)
    assert result == 25  # (20 + 30) / 2 = 25

def test_store_temperature_in_minio():
    """Test storing temperature data in MinIO."""
    with patch("app.storage.minio_client.put_object") as mock_put_object:
        store_temperature_in_minio(25)
        mock_put_object.assert_called_once()

def test_temperature_endpoint_cache_hit():
    """Test the /temperature endpoint with a cache hit."""
    with patch("app.config.redis_client.get") as mock_redis_get:
        mock_redis_get.return_value = b"20"  # Simulate cached data

        response = client.get("/temperature")
        assert response.status_code == 200
        assert response.json() == {"temperature": 20, "status": "Good"}

def test_temperature_endpoint_cache_miss():
    """Test the /temperature endpoint with a cache miss."""
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

    with patch("app.config.redis_client.get") as mock_redis_get, patch("app.services.fetch_temperature_from_api") as mock_fetch:
        mock_redis_get.return_value = None  # Simulate cache miss
        mock_fetch.return_value = mock_response

        response = client.get("/temperature")
        assert response.status_code == 200
        assert response.json() == {"temperature": 20, "status": "Good"}