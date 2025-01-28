"""This module contains the Prometheus metrics for the application."""
from prometheus_client import REGISTRY, Counter, Histogram, generate_latest

# Initialize logging and Prometheus metrics.
cache_hit = Counter("cache_hit", "Number of cache hits")
cache_miss = Counter("cache_miss", "Number of cache misses")
api_response_time = Histogram('api_response_time_seconds', 'API response time in seconds')

def get_metrics():
    """Return the Prometheus metrics."""
    return generate_latest(REGISTRY)