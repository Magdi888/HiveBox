"""
This module handles the application endpoints.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
import semantic_version
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from app.storage import store_temperature_in_minio, store_temperature_periodically
from app.health import readiness_check
from app.metrics import get_metrics
from app.services import get_temperature


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return PlainTextResponse(get_metrics())
@app.get("/temperature")
async def temperature():
    """Return the average temperature."""
    try:
        return get_temperature()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/store")
async def store_temperature_direct():
    """Store temperature data in MinIO directly."""
    current_temperature = get_temperature()
    store_temperature_in_minio(current_temperature["temperature"])


@app.get("/readyz")
async def readyz():
    """Check if the application is ready."""
    readiness_status, status_code = readiness_check()
    return JSONResponse(content=readiness_status, status_code=status_code)
    