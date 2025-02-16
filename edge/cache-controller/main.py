from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import asyncio
from datetime import datetime, timedelta
import logging
from pydantic import validator
from pydantic_settings import BaseSettings
import os
from minio import Minio
from typing import Dict, List, Tuple
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.debug("Starting application initialization")

class Settings(BaseSettings):
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: str = os.getenv("REDIS_PORT", "6379")
    redis_channel: str = os.getenv("REDIS_CHANNEL", "cache_misses")
    
    minio_cache_host: str = os.getenv("MINIO_CACHE_HOST", "minio-cache")
    minio_cache_port: str = os.getenv("MINIO_CACHE_PORT", "9000")
    minio_core_host: str = os.getenv("MINIO_CORE_HOST", "minio-core")
    minio_core_port: str = os.getenv("MINIO_CORE_PORT", "9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    cache_bucket: str = os.getenv("CACHE_BUCKET", "cache")
    core_bucket: str = os.getenv("CORE_BUCKET", "videos")
    
    # Caching thresholds
    min_miss_count: int = int(os.getenv("MIN_MISS_COUNT", "3"))
    time_window_hours: int = int(os.getenv("TIME_WINDOW_HOURS", "24"))
    
    @validator('redis_port')
    def parse_redis_port(cls, v):
        if ":" in v:
            return int(v.split(":")[-1])
        return int(v)
    
    class Config:
        env_file = ".env"

logger.debug("Initializing FastAPI application")
app = FastAPI(title="Cache Controller Service")

logger.debug("Adding CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


logger.debug("Loading settings")
settings = Settings()
logger.debug(f"Settings loaded: REDIS_HOST={settings.redis_host}, REDIS_PORT={settings.redis_port}")

logger.debug("Initializing MinIO clients")
# logger = logging.getLogger(__name__)

try:
    # Initialize MinIO clients
    minio_cache_client = Minio(
        f"{settings.minio_cache_host}:{settings.minio_cache_port}",
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False
    )
    logger.debug("MinIO cache client initialized")

    minio_core_client = Minio(
        f"{settings.minio_core_host}:{settings.minio_core_port}",
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False
    )
    logger.debug("MinIO core client initialized")
except Exception as e:
    logger.error(f"Failed to initialize MinIO clients: {e}")
    raise

# Cache statistics
cache_stats = {
    'pending_caches': set(),
    'cached_files': set()
}

async def analyze_miss_pattern(redis_client: redis.Redis, video_id: str, file_name: str) -> Tuple[int, List[str]]:
    """
    Analyze the miss pattern for a specific file
    Returns tuple of (miss_count, timestamps)
    """
    key = f"missed:{video_id}/{file_name}"
    try:
        data = redis_client.get(key)
        if data:
            miss_data = json.loads(data)
            return miss_data["count"], miss_data["timestamps"]
        return 0, []
    except Exception as e:
        logger.error(f"Error analyzing miss pattern: {e}")
        return 0, []

async def should_cache_file(redis_client: redis.Redis, video_id: str, file_name: str) -> bool:
    """
    Determine if a file should be cached based on:
    1. Number of misses
    2. Frequency of misses in recent time window
    3. Not already cached or pending
    """
    object_path = f"hls/{video_id}/{file_name}"
    
    # Check if already cached or pending
    if (object_path in cache_stats['cached_files'] or 
        object_path in cache_stats['pending_caches']):
        return False
    
    # Get miss data
    miss_count, timestamps = await analyze_miss_pattern(redis_client, video_id, file_name)
    
    if miss_count < settings.min_miss_count:
        return False
        
    # Convert timestamps to datetime objects
    timestamps = [datetime.fromisoformat(ts) for ts in timestamps]
    
    # Check if we have enough recent misses
    recent_threshold = datetime.now() - timedelta(hours=settings.time_window_hours)
    recent_misses = [ts for ts in timestamps if ts > recent_threshold]
    
    # Cache if we have enough recent misses
    return len(recent_misses) >= settings.min_miss_count

async def cache_file(video_id: str, file_name: str):
    """Copy file from core storage to cache"""
    try:
        object_path = f"hls/{video_id}/{file_name}"
        cache_stats['pending_caches'].add(object_path)
        
        # Get object from core storage
        data = minio_core_client.get_object(
            settings.core_bucket,
            object_path
        )
        
        # Put object in cache storage
        minio_cache_client.put_object(
            settings.cache_bucket,
            object_path,
            data,
            length=-1,
            part_size=10*1024*1024
        )
        
        logger.info(f"Successfully cached: {object_path}")
        cache_stats['cached_files'].add(object_path)
        cache_stats['pending_caches'].remove(object_path)
        
    except Exception as e:
        logger.error(f"Error caching file {object_path}: {e}")
        cache_stats['pending_caches'].remove(object_path)
        raise

async def process_cache_miss(redis_client: redis.Redis, message: Dict):
    """Process a cache miss event and decide whether to cache the file"""
    try:
        video_id = message.get('video_id')
        file_name = message.get('file_name')
        
        if not video_id or not file_name:
            logger.error(f"Invalid message format: {message}")
            return
            
        should_cache = await should_cache_file(redis_client, video_id, file_name)
        
        if should_cache:
            logger.info(f"Initiating caching for {video_id}/{file_name}")
            await cache_file(video_id, file_name)
        else:
            logger.debug(f"Skipping cache for {video_id}/{file_name} based on current patterns")
            
    except Exception as e:
        logger.error(f"Error processing cache miss: {e}")

async def redis_subscriber():
    """Subscribe to Redis cache miss channel and process messages"""
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True
    )
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(settings.redis_channel)
    
    logger.info("Started Redis subscriber")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    logger.info(f"Processing cache miss for: {data}")
                    await process_cache_miss(redis_client, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in message: {message['data']}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    finally:
        pubsub.unsubscribe()
        redis_client.close()

@app.on_event("startup")
async def startup_event():
    """Start the Redis subscriber on startup"""
    logger.debug("Entering startup event")
    try:
        # Try to establish Redis connection first
        logger.debug(f"Attempting to connect to Redis at {settings.redis_host}:{settings.redis_port}")
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )
        # Test the connection
        redis_client.ping()
        logger.debug("Redis connection successful")
        redis_client.close()
        
        # Start redis_subscriber in the background
        logger.debug("Creating Redis subscriber task")
        asyncio.create_task(redis_subscriber())
        logger.debug("Successfully created Redis subscriber task")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.get("/stats")
async def get_cache_stats():
    """Get current cache statistics"""
    return {
        "pending_caches": list(cache_stats['pending_caches']),
        "cached_files": list(cache_stats['cached_files']),
        "pending_count": len(cache_stats['pending_caches']),
        "cached_count": len(cache_stats['cached_files'])
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}