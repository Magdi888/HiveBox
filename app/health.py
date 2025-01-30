"""This module for health monitoring of the application."""
import logging
import requests
import redis
from fastapi import status
from app.services import count_available_senseboxes
from app.storage import redis_client


logger = logging.getLogger(__name__)
def readiness_check():
    """
    Health check endpoint to verify if the application is ready to serve requests.
    Returns HTTP 200 unless:
    - 50% + 1 of the configured senseBoxes are not accessible.
    - AND caching content is older than 5 minutes.
    """
    try:
        # Check if cached content is older than 5 minutes
        cached_temperature = redis_client.get('temperature')
        if cached_temperature:
            cache_timestamp = redis_client.ttl('temperature')  # Time to live in seconds
            logger.info("Cache TTL: %s", cache_timestamp)
            if cache_timestamp is not None and 0 < cache_timestamp < 300:  # 300 seconds = 5 minutes
                logger.info("Cached content is fresh.")
                return {"status": "ready", "message": "Application is ready"}, status.HTTP_200_OK

        # Check accessibility of senseBoxes
        total_boxes, inaccessible_boxes = count_available_senseboxes()
        logger.info("Total senseBoxes: %d, Inaccessible senseBoxes: %d", total_boxes, inaccessible_boxes)

        if total_boxes == 0:
            logger.error("No senseBoxes found.")
            return {"status": "error", "message": "No senseBoxes found"}, status.HTTP_503_SERVICE_UNAVAILABLE

        inaccessible_percentage = (inaccessible_boxes / total_boxes) * 100
        logger.info("Inaccessible senseBoxes: %d/%d (%.2f%%)", inaccessible_boxes, total_boxes, inaccessible_percentage)

        # Determine if the application is ready
        if inaccessible_percentage >= 50:
            logger.error("Application is not ready: More than 50% of senseBoxes are inaccessible")
            return {"status": "unavailable", "message": "More than 50% of senseBoxes are inaccessible."}, status.HTTP_503_SERVICE_UNAVAILABLE
        
        logger.info("Application is ready")
        return {"status": "ready", "message": "Application is ready"}, status.HTTP_200_OK

    except (requests.RequestException, redis.RedisError) as e:
        logger.error("Error checking senseBox accessibility or cached data: %s", e)
        return {"status": "error", "message": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE
