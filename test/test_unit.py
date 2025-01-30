"""Unit tests for the FastAPI application."""
import unittest
from unittest.mock import patch
from fastapi import status, HTTPException
import redis
import requests
from app.health import readiness_check
from app.services import get_temperature, fetch_temperature_from_api, calculate_average_temperature

class FetchTemperatureFromApiTestCase(unittest.TestCase):
    """Test cases for the fetch_temperature_from_api service."""
    @patch('app.services.requests.get')
    def test_api_request_fails(self, mock_get):
        """Test that the service raises an exception when the API request fails."""
        mock_get.side_effect = Exception('Request failed')
        with self.assertRaises(Exception):
            fetch_temperature_from_api()
    @patch('app.services.requests.get')
    def test_api_request_successful(self, mock_get):
        """Test that the service returns the API response."""
        mock_response = unittest.mock.Mock()
        mock_response.json.return_value = {'key': 'value'}
        mock_get.return_value = mock_response
        result = fetch_temperature_from_api()
        self.assertEqual(result, {'key': 'value'})

class TestCalculateAverageTemperature(unittest.TestCase):
    """Test cases for the calculate_average_temperature service."""
    def test_valid_response_data(self):
        """Test that the service returns the average temperature."""
        response = [
            {
                "sensors": [
                    {"title": "Temperatur", "lastMeasurement": {"value": "20"}},
                    {"title": "Temperatur", "lastMeasurement": {"value": "30"}}
                ]
            }
        ]
        expected_result = 25
        self.assertEqual(calculate_average_temperature(response), expected_result)
    def test_no_temperature_data(self):
        """Test that the service raises an exception when there is no temperature data."""
        response = [
            {
                "sensors": [
                    {"title": "Humidity", "lastMeasurement": {"value": "50"}}
                ]
            }
        ]
        with self.assertRaises(HTTPException) as e:
            calculate_average_temperature(response)
        self.assertEqual(e.exception.status_code, 404)
        self.assertEqual(e.exception.detail, "No temperature data found")
    def test_invalid_response_data(self):
        """Test that the service raises an exception when the temperature data is invalid."""
        response = [
            {
                "sensors": [
                    {"title": "Temperatur", "lastMeasurement": {"value": "abc"}}
                ]
            }
        ]
        with self.assertRaises(ValueError):
            calculate_average_temperature(response)
    def test_empty_response_data(self):
        """Test that the service raises an exception when the response data is empty."""
        response = []
        with self.assertRaises(HTTPException) as e:
            calculate_average_temperature(response)
        self.assertEqual(e.exception.status_code, 404)
        self.assertEqual(e.exception.detail, "No temperature data found")
class TestGetTemperature(unittest.TestCase):
    """Test cases for the get_temperature service."""
    @patch('app.services.redis_client')
    def test_cache_hit(self, mock_redis_client):
        """Test that the service returns the cached temperature."""
        mock_redis_client.get.return_value = b'20'
        result = get_temperature()
        self.assertEqual(result, {"temperature": 20, "status": "Good"})
        mock_redis_client.get.assert_called_once_with('temperature')

    @patch('app.services.redis_client')
    @patch('app.services.fetch_temperature_from_api')
    @patch('app.services.calculate_average_temperature')
    def test_cache_miss_valid_data(self, mock_calculate_average_temperature, mock_fetch_temperature_from_api, mock_redis_client):
        """Test that the service fetches the temperature from the API and caches it."""
        mock_redis_client.get.return_value = None
        mock_fetch_temperature_from_api.return_value = [{"sensors": [{"title": "Temperatur", "lastMeasurement": {"value": "20"}}]}]
        mock_calculate_average_temperature.return_value = 20
        result = get_temperature()
        self.assertEqual(result, {"temperature": 20, "status": "Good"})
        mock_redis_client.get.assert_called_once_with('temperature')
        mock_fetch_temperature_from_api.assert_called_once()
        mock_calculate_average_temperature.assert_called_once()

    @patch('app.services.redis_client')
    @patch('app.services.fetch_temperature_from_api')
    @patch('app.services.calculate_average_temperature')
    def test_cache_miss_invalid_data(self, mock_calculate_average_temperature, mock_fetch_temperature_from_api, mock_redis_client):
        """Test that the service raises an exception when no valid temperature data is found."""
        mock_redis_client.get.return_value = None
        mock_fetch_temperature_from_api.return_value = [{"sensors": [{"title": "Invalid", "lastMeasurement": {"value": "20"}}]}]
        mock_calculate_average_temperature.side_effect = HTTPException(status_code=404, detail="No temperature data found")
        with self.assertRaises(HTTPException):
            get_temperature()
        mock_redis_client.get.assert_called_once_with('temperature')
        mock_fetch_temperature_from_api.assert_called_once()
        mock_calculate_average_temperature.assert_called_once()

    @patch('app.services.redis_client')
    def test_temperature_status_too_cold(self, mock_redis_client):
        """Test that the service returns the correct temperature status for different temperatures."""
        mock_redis_client.get.return_value = b'5'
        result = get_temperature()
        self.assertEqual(result, {"temperature": 5, "status": "Too cold"})

    @patch('app.services.redis_client')
    def test_temperature_status_good(self, mock_redis_client):
        """Test that the service returns the correct temperature status for different temperatures."""
        mock_redis_client.get.return_value = b'20'
        result = get_temperature()
        self.assertEqual(result, {"temperature": 20, "status": "Good"})

    @patch('app.services.redis_client')
    def test_temperature_status_too_hot(self, mock_redis_client):
        """Test that the service returns the correct temperature status for different temperatures."""
        mock_redis_client.get.return_value = b'40'
        result = get_temperature()
        self.assertEqual(result, {"temperature": 40, "status": "Too hot"})

class TestReadinessCheck(unittest.TestCase):
    """Test cases for the readiness_check service."""
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_cached_content_fresh_all_senseboxes_accessible(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns True when all senseboxes are accessible and the cache is fresh."""
        mock_redis_client.get.return_value = b'20'
        mock_redis_client.ttl.return_value = 100
        mock_count_available_senseboxes.return_value = (10, 0)
        result = readiness_check()
        self.assertEqual(result, ({"status": "ready", "message": "Application is ready"}, status.HTTP_200_OK))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_cached_content_fresh_more_than_50_percent_inaccessible(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when more than 50% of senseboxes are inaccessible and the cache is fresh."""
        mock_redis_client.get.return_value = b'20'
        mock_redis_client.ttl.return_value = 100
        mock_count_available_senseboxes.return_value = (10, 6)
        result = readiness_check()
        self.assertEqual(result, ({"status": "ready", "message": "Application is ready"}, status.HTTP_200_OK))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_cached_content_stale_all_senseboxes_accessible(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when all senseboxes are accessible and the cache is stale."""
        mock_redis_client.get.return_value = None
        mock_count_available_senseboxes.return_value = (10, 0)
        result = readiness_check()
        self.assertEqual(result, ({"status": "ready", "message": "Application is ready"}, status.HTTP_200_OK))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_cached_content_stale_more_than_50_percent_inaccessible(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when more than 50% of senseboxes are inaccessible and the cache is stale."""
        mock_redis_client.get.return_value = None
        mock_count_available_senseboxes.return_value = (10, 6)
        result = readiness_check()
        self.assertEqual(result, ({"status": "unavailable", "message": "More than 50% of senseBoxes are inaccessible."}, status.HTTP_503_SERVICE_UNAVAILABLE))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_no_senseboxes_found(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when no senseboxes are found."""
        mock_redis_client.ttl.return_value = 310
        mock_redis_client.get.return_value = b'20'
        mock_count_available_senseboxes.return_value = (0, 0)
        result = readiness_check()
        self.assertEqual(result, ({"status": "error", "message": "No senseBoxes found"}, status.HTTP_503_SERVICE_UNAVAILABLE))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_error_checking_sensebox_accessibility(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when there is an error checking sensebox accessibility."""
        mock_redis_client.get.return_value = None
        mock_count_available_senseboxes.side_effect = requests.RequestException('Error')
        result = readiness_check()
        self.assertEqual(result, ({"status": "error", "message": "Error"}, status.HTTP_503_SERVICE_UNAVAILABLE))
    @patch('app.health.count_available_senseboxes')
    @patch('app.health.redis_client')
    def test_error_checking_cached_content(self, mock_redis_client, mock_count_available_senseboxes):
        """Test that the service returns False when there is an error checking cached content."""
        mock_redis_client.get.side_effect = redis.RedisError('Error')
        mock_count_available_senseboxes.return_value = (10, 0)
        result = readiness_check()
        self.assertEqual(result, ({"status": "error", "message": "Error"}, status.HTTP_503_SERVICE_UNAVAILABLE))