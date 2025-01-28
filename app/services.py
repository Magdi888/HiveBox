"""This module contains the services that are used to fetch data from the OpenSenseMap API and store it in the MinIO storage."""
from datetime import datetime
import logging
import time
import requests
from fastapi import HTTPException
from app.config import OPENSENSEMAP_URL
from app.metrics import cache_hit, api_response_time, cache_miss
from app.config import CACHE_EXPIRATION, redis_client



logger = logging.getLogger(__name__)

def fetch_temperature_from_api():
    """Fetch temperature data from OpenSenseMap API."""
    data_format = "json"
    phenomenon = "temperature"
    date = datetime.now().isoformat() + "Z"
    try:
        response = requests.get(
            f'{OPENSENSEMAP_URL}/boxes?date={date}&phenomenon={phenomenon}&format={data_format}',
            timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error("Error fetching temperature data from OpenSenseMap API: %s", e)
        raise e

def calculate_average_temperature(response):
    """Calculate the average temperature from the OpenSenseMap API response."""
    measurement = 0
    counter = 0
    for box in response:
        for sensor in box.get("sensors", []):
            if sensor.get("title") == "Temperatur":
                counter += 1
                measurement += float(sensor["lastMeasurement"]["value"])
    if counter == 0:
        raise HTTPException(status_code=404, detail="No temperature data found")
    return int(measurement / counter)
def get_temperature():
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
        response = fetch_temperature_from_api()
        data = calculate_average_temperature(response)
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
    
def check_sensboxes_available():
    """Check if senseBoxes are available."""
    try:
        response = fetch_temperature_from_api()
        boxes = response

        # Count total senseBoxes and inaccessible ones
        total_boxes = len(boxes)
        inaccessible_boxes = 0

        for box in boxes:
            try:
                # Check if the box is accessible by fetching its sensors
                box_id = box["_id"]
                box_response = requests.get(
                    f'{OPENSENSEMAP_URL}/boxes/{box_id}/sensors',
                    timeout=10)
                if box_response.status_code != 200:
                    inaccessible_boxes += 1
            except requests.RequestException:
                inaccessible_boxes += 1

        return total_boxes, inaccessible_boxes
    except requests.RequestException as e:
        logger.error("Error checking senseBox accessibility: %s", e)
        raise
