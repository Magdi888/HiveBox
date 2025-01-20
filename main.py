"""
This module handles the application endpoints.
"""
import asyncio
import datetime
import io
import json
import logging
import os
import time
from contextlib import asynccontextmanager
import redis
import requests
import semantic_version
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from minio import Minio
from minio.error import S3Error
from prometheus_client import REGISTRY, Counter, Histogram, generate_latest

# Initialize logging and Prometheus metrics.
cache_hit = Counter("cache_hit", "Number of cache hits")
cache_miss = Counter("cache_miss", "Number of cache misses")
api_response_time = Histogram('api_response_time_seconds', 'API response time in seconds')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Redis client and cache expiration time.
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')
redis_client = redis.Redis(host=redis_host, port=redis_port)
CACHE_EXPIRATION = 300
# Load MinIO configuration from environment variables
minio_endpoint = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
minio_access_key = os.environ.get('MINIO_ACCESS_KEY', 'your_access_key')
minio_secret_key = os.environ.get('MINIO_SECRET_KEY', 'your_secret_key')
minio_bucket = os.environ.get('MINIO_BUCKET', 'temperature-data')

# Initialize MinIO client

minio_client = Minio(
    minio_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False
)

# Check if the MinIO bucket exists, if not create it
if not minio_client.bucket_exists(minio_bucket):
    try:
        minio_client.make_bucket(minio_bucket)
    except S3Error as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Failed to create MinIO bucket") from e
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan event handler for FastAPI."""
    # Start the background task
    task = asyncio.create_task(store_temperature_periodically())
    yield
    # Clean up on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Background task cancelled")

# Initialize FastAPI app.
app = FastAPI(lifespan=lifespan)
@app.get("/version")
async def version():
    """Return a application version."""
    app_version = semantic_version.Version('0.0.1')
    return str(app_version)

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return PlainTextResponse(generate_latest(REGISTRY))
@app.get("/temperature")
async def temperature():
    """Return average temperature based on all sensebox data"""
    cached_temperature = redis_client.get('temperature')
    if cached_temperature:
        cache_hit.inc()
        logger.info("Data retrieved from cache")
        data = int(cached_temperature.decode('utf-8'))
    else:
        cache_miss.inc()
        logger.info("Data retrieved from OpenSenseMap API")
        start_time= time.time()
        data_format = "json"
        phenomenon = "temperature"
        open_sense_map_url = os.environ.get('OPENSENSEMAP_URL', "https://api.opensensemap.org")
        date = datetime.datetime.now().isoformat() + "Z"
        try:
            req = requests.get(
                f'{open_sense_map_url}/boxes?date={date}&phenomenon={phenomenon}&format={data_format}',
                timeout=120)
            response = req.json()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        measurement = 0
        counter = 0
        for box in response:
            for sensor in box.get("sensors",[]):
                if sensor.get("title") == "Temperatur":
                    counter += 1
                    measurement += float(sensor["lastMeasurement"]["value"])
        if counter == 0:
            raise HTTPException(status_code=404, detail="No Temp data found")
        data = measurement / counter
        data = int(data)
        redis_client.set('temperature', data, ex=CACHE_EXPIRATION)
        logger.info("Data stored in cache")
        api_response_time.observe(time.time() - start_time)

    match data:
        case _ if data < 10:
            return {"temperature": data, "status": "Too cold"}
        case _ if data >= 11 or data <= 36:
            return {"temperature": data, "status": "Good"}
        case _ if data > 37:
            return {"temperature": data, "status": "Too hot"}
        case _:
            raise HTTPException(status_code=404, detail="No Temp data found")
@app.get("/store")
async def store_temperature_direct():
    """Store temperature data in MinIO directly."""
    current_temperature = await temperature()
    store_temperature_in_minio(current_temperature["temperature"])


@app.get("/readyz")
async def readiness_check():
    """
    Health check endpoint to verify if the application is ready to serve requests.
    Returns HTTP 200 unless:
    - 50% + 1 of the configured senseBoxes are not accessible.
    - AND caching content is older than 5 minutes.
    """
    # Check if cached content is older than 5 minutes
    cached_temperature = redis_client.get('temperature')
    if cached_temperature:
        cache_timestamp = redis_client.ttl('temperature')  # Time to live in seconds
        if cache_timestamp < 300:  # 300 seconds = 5 minutes
            logger.info("Cached content is fresh.")
        else:
            logger.warning("Cached content is older than 5 minutes.")
    else:
        logger.warning("No cached content found.")

    # Check accessibility of senseBoxes
    try:
        data_format = "json"
        phenomenon = "temperature"
        open_sense_map_url = os.environ.get('OPENSENSEMAP_URL', "https://api.opensensemap.org")
        date = datetime.datetime.now().isoformat() + "Z"
        response = requests.get(
            f'{open_sense_map_url}/boxes?date={date}&phenomenon={phenomenon}&format={data_format}',
            timeout=120)
        boxes = response.json()

        # Count total senseBoxes and inaccessible ones
        total_boxes = len(boxes)
        inaccessible_boxes = 0

        for box in boxes:
            try:
                # Check if the box is accessible by fetching its sensors
                box_id = box["_id"]
                box_response = requests.get(
                    f'{open_sense_map_url}/boxes/{box_id}/sensors',
                    timeout=10)
                if box_response.status_code != 200:
                    inaccessible_boxes += 1
            except requests.RequestException:
                inaccessible_boxes += 1

        # Calculate the percentage of inaccessible senseBoxes
        if total_boxes == 0:
            logger.error("No senseBoxes found.")
            return {"status": "error", "message": "No senseBoxes found"}, status.HTTP_503_SERVICE_UNAVAILABLE

        inaccessible_percentage = (inaccessible_boxes / total_boxes) * 100
        logger.info("Inaccessible senseBoxes: %d/%d (%.2f%%)", inaccessible_boxes, total_boxes, inaccessible_percentage)

        # Determine if the application is ready
        if inaccessible_percentage > 50 and (not cached_temperature or cache_timestamp >= 300):
            logger.error("Application is not ready: More than 50% of senseBoxes are inaccessible AND cached content is stale.")
            return {"status": "unavailable", "message": "More than 50% of senseBoxes are inaccessible AND cached content is stale"}, status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            logger.info("Application is ready.")
            return {"status": "ready"}, status.HTTP_200_OK

    except requests.RequestException as e:
        logger.error("Error checking senseBox accessibility: %s", e)
        return {"status": "error", "message": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE
def store_temperature_in_minio(temp: int):
    """Store temperature data in MinIO."""
    try:
        timestamp = datetime.datetime.now().isoformat()
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
            minio_bucket,
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
                current_temperature = int(cached_temperature.decode('utf-8'))
                store_temperature_in_minio(current_temperature)
            else:
                # If not cached, call the /temperature endpoint to fetch the data
                logger.info("Data not cached. Fetching from OpenSenseMap API...")
                try:
                # Call the temperature() function directly
                    result = await temperature()
                    temperature_value = result["temperature"]
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
