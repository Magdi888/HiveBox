""" Configuration file for the application. """
import os
import redis

# Redis configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
CACHE_EXPIRATION = 300  # 5 minutes

# MinIO configuration
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'your_access_key')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'your_secret_key')
MINIO_BUCKET = os.environ.get('MINIO_BUCKET', 'temperature-data')

# OpenSenseMap API configuration
OPENSENSEMAP_URL = os.environ.get('OPENSENSEMAP_URL', "https://api.opensensemap.org")
# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)