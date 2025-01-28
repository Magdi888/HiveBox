"""Integration tests for the FastAPI application."""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.api import app

# Initialize the FastAPI test client
client = TestClient(app)

def test_temperature_endpoint_integration():
    """Test the /temperature endpoint with Redis."""
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


def test_readyz_endpoint_integration():
    """Test the /readyz endpoint with Redis and OpenSenseMap API integration."""
    mock_response = [
                {
                "_id": "59721243fe1c7400113446fc",
                "createdAt": "2022-03-30T11:25:43.328Z",
                "updatedAt": "2025-01-26T10:38:29.178Z",
                "name": "M_Office_1",
                "grouptag": [
                    "Sofia"
                ],
                "exposure": "indoor",
                "sensors": [
                    {
                    "title": "PM10",
                    "unit": "µg/m³",
                    "sensorType": "SDS 011",
                    "icon": "osem-cloud",
                    "_id": "59721243fe1c740011344701",
                    "lastMeasurement": {
                        "value": "4.00",
                        "createdAt": "2023-10-03T13:01:16.694Z"
                    }
                    },
                    {
                    "title": "PM2.5",
                    "unit": "µg/m³",
                    "sensorType": "SDS 011",
                    "icon": "osem-cloud",
                    "_id": "59721243fe1c740011344700",
                    "lastMeasurement": {
                        "value": "2.23",
                        "createdAt": "2023-10-03T13:01:16.694Z"
                    }
                    },
                    {
                    "title": "Temperatur",
                    "unit": "°C",
                    "sensorType": "BME280",
                    "icon": "osem-thermometer",
                    "_id": "59721243fe1c7400113446ff",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "22.73"
                    }
                    },
                    {
                    "title": "rel. Luftfeuchte",
                    "unit": "%",
                    "sensorType": "BME280",
                    "icon": "osem-humidity",
                    "_id": "59721243fe1c7400113446fe",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "35.09"
                    }
                    },
                    {
                    "title": "Luftdruck",
                    "unit": "Pa",
                    "sensorType": "BME280",
                    "icon": "osem-barometer",
                    "_id": "59721243fe1c7400113446fd",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "95439.83"
                    }
                    },
                    {
                    "_id": "5aab7571396417001b724228",
                    "icon": "osem-thermometer",
                    "sensorType": "HTU21D",
                    "unit": "°C",
                    "title": "temperature",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "22.39"
                    }
                    },
                    {
                    "_id": "5aab7571396417001b724229",
                    "icon": "osem-humidity",
                    "sensorType": "HTU21D",
                    "unit": "%",
                    "title": "humidity",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "28.33"
                    }
                    }
                ],
                "model": "luftdaten_sds011_bme280",
                "currentLocation": {
                    "type": "Point",
                    "coordinates": [
                    23.405557,
                    42.636516
                    ],
                    "timestamp": "2022-07-28T06:42:45.501Z"
                },
                "lastMeasurementAt": "2025-01-26T10:38:29.170Z",
                "loc": [
                    {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                        23.405557,
                        42.636516
                        ],
                        "timestamp": "2022-07-28T06:42:45.501Z"
                    },
                    "type": "Feature"
                    }
                ]
                }

    ]

    with patch("app.config.redis_client.get") as mock_redis_get, \
        patch("app.services.fetch_temperature_from_api") as mock_fetch, \
        patch("app.config.redis_client.ttl") as mock_redis_ttl:
        mock_redis_get.return_value = b"20"  # Simulate cached data
        mock_redis_ttl.return_value = 115  # Simulate cache freshness
        mock_fetch.return_value = mock_response

        response = client.get("/readyz")
        print("Response Status Code:", response.status_code)
        print("Response JSON:", response.json())
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "message": "Application is ready"}

def test_readyz_endpoint_failure():
    """Test the /readyz endpoint when more than 50% of senseBoxes are inaccessible."""
    mock_response = [
                {   
                "_id": "59721243fe1c7400113446fc",
                "createdAt": "2022-03-30T11:25:43.328Z",
                "updatedAt": "2025-01-26T10:38:29.178Z",
                "name": "M_Office_1",
                "grouptag": [
                    "Sofia"
                ],
                "exposure": "indoor",
                "sensors": [
                    {
                    "title": "PM10",
                    "unit": "µg/m³",
                    "sensorType": "SDS 011",
                    "icon": "osem-cloud",
                    "_id": "59721243fe1c740011344701",
                    "lastMeasurement": {
                        "value": "4.00",
                        "createdAt": "2023-10-03T13:01:16.694Z"
                    }
                    },
                    {
                    "title": "PM2.5",
                    "unit": "µg/m³",
                    "sensorType": "SDS 011",
                    "icon": "osem-cloud",
                    "_id": "59721243fe1c740011344700",
                    "lastMeasurement": {
                        "value": "2.23",
                        "createdAt": "2023-10-03T13:01:16.694Z"
                    }
                    },
                    {
                    "title": "Temperatur",
                    "unit": "°C",
                    "sensorType": "BME280",
                    "icon": "osem-thermometer",
                    "_id": "59721243fe1c7400113446ff",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "22.73"
                    }
                    },
                    {
                    "title": "rel. Luftfeuchte",
                    "unit": "%",
                    "sensorType": "BME280",
                    "icon": "osem-humidity",
                    "_id": "59721243fe1c7400113446fe",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "35.09"
                    }
                    },
                    {
                    "title": "Luftdruck",
                    "unit": "Pa",
                    "sensorType": "BME280",
                    "icon": "osem-barometer",
                    "_id": "59721243fe1c7400113446fd",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "95439.83"
                    }
                    },
                    {
                    "_id": "5aab7571396417001b724228",
                    "icon": "osem-thermometer",
                    "sensorType": "HTU21D",
                    "unit": "°C",
                    "title": "temperature",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "22.39"
                    }
                    },
                    {
                    "_id": "5aab7571396417001b724229",
                    "icon": "osem-humidity",
                    "sensorType": "HTU21D",
                    "unit": "%",
                    "title": "humidity",
                    "lastMeasurement": {
                        "createdAt": "2025-01-26T10:38:29.170Z",
                        "value": "28.33"
                    }
                    }
                ],
                "model": "luftdaten_sds011_bme280",
                "currentLocation": {
                    "type": "Point",
                    "coordinates": [
                    23.405557,
                    42.636516
                    ],
                    "timestamp": "2022-07-28T06:42:45.501Z"
                },
                "lastMeasurementAt": "2025-01-26T10:38:29.170Z",
                "loc": [
                    {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                        23.405557,
                        42.636516
                        ],
                        "timestamp": "2022-07-28T06:42:45.501Z"
                    },
                    "type": "Feature"
                    }
                ]
                },
                {
                    "_id": "box2",
                    "sensors": []
                }
    ]

    with patch("app.config.redis_client.get") as mock_redis_get, \
        patch("app.services.fetch_temperature_from_api") as mock_fetch, \
        patch("app.config.redis_client.ttl") as mock_redis_ttl:
        mock_redis_get.return_value = b"20"  # Simulate cached data
        mock_redis_ttl.return_value = 115
        mock_fetch.return_value = mock_response


        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "message": "More than 50% of senseBoxes are inaccessible."}