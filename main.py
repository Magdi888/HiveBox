"""
This module handles the application versioning using semantic_version.
"""
import datetime

import semantic_version

from fastapi import FastAPI, HTTPException
import requests

app = FastAPI()
@app.get("/version")
async def version():
    """Return a application version."""
    app_version = semantic_version.Version('0.0.1')
    return str(app_version)

@app.get("/temperature")
async def temperature():
    """Return average temperature based on all sensebox data"""
    data_format = "json"
    phenomenon = "temperature"
    date = datetime.datetime.now().isoformat() + "Z"
    try:
        req = requests.get(
            f'https://api.opensensemap.org/boxes?date={date}&phenomenon={phenomenon}&format={data_format}',
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
    return {"message": f"The average Temp is {round(data, 2)}"}