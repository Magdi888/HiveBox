"""Storage module for storing temperature data in Redis and MinIO."""
import asyncio
import json
import io
from datetime import datetime
import logging
from fastapi import HTTPException
import requests
import redis
from minio import Minio
from minio.error import S3Error
from app.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, redis_client
from app.services import fetch_temperature_from_api, calculate_average_temperature


logger = logging.getLogger(__name__)

# Initialize Redis client


# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)


def store_temperature_in_minio(temp: int):
    """Store temperature data in MinIO."""
    # Ensure the bucket exists
    if not minio_client.bucket_exists(MINIO_BUCKET):
        try:
            minio_client.make_bucket(MINIO_BUCKET)
        except S3Error as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail="Failed to create MinIO bucket") from e
    try:
        timestamp = datetime.now().isoformat()
        data = {
            "timestamp": timestamp,
            "temperature": temp
        }

        object_name = f"temperature_{timestamp}.json"
        logger.info("Storing data in MinIO: %s", data)
        # convert data to bytes
        data_bytes = json.dumps(data).encode('utf-8')
        data_stream = io.BytesIO(data_bytes)

        minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            data_stream,
            len(data_bytes)
        )
        logger.info("Stored temperature data in MinIO: %s", object_name)
    except S3Error as e:
        logger.error("S3Error storing temperature data in MinIO: %s", e)
async def store_temperature_periodically():
    """Store temperature data in MinIO every 5 minutes."""
    while True:
        try:
            cached_temperature = redis_client.get('temperature')
            if cached_temperature:
                # If cached, store it in MinIO
                current_temperature = int(cached_temperature)
                store_temperature_in_minio(current_temperature)
            else:
                # If not cached, fetch the data
                logger.info("Data not cached. Fetching from OpenSenseMap API...")
                try:
                # Get the temperature data from OpenSenseMap API
                    temperature_value = calculate_average_temperature(fetch_temperature_from_api())
                    store_temperature_in_minio(temperature_value)
                except HTTPException as e:
                    logger.error("Failed to fetch temperature data: %s", e.detail)
                except (ValueError, TypeError) as e:
                    logger.error("Unexpected error: %s", e)
        except (requests.RequestException, redis.RedisError, S3Error) as e:
            logger.error("Error in background task: %s", e)

        # Wait for 5 minutes
        logger.info("Waiting for 5 minutes before next check...")
        await asyncio.sleep(300)