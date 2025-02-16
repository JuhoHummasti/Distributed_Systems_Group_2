from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import redis
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client.exposition import generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
import json
import asyncio
from datetime import datetime, timedelta
import logging
from pydantic import validator
from pydantic_settings import BaseSettings
import os
from minio import Minio
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    min_miss_count: int = int(os.getenv("MIN_MISS_COUNT", "3"))
    time_window_hours: int = int(os.getenv("TIME_WINDOW_HOURS", "24"))
    
    @validator('redis_port')
    def parse_redis_port(cls, v):
        if ":" in v:
            return int(v.split(":")[-1])
        return int(v)
    
    class Config:
        env_file = ".env"

app = FastAPI(title="Cache Controller Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = Settings()

minio_cache_client = Minio(
    f"{settings.minio_cache_host}:{settings.minio_cache_port}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)

minio_core_client = Minio(
    f"{settings.minio_core_host}:{settings.minio_core_port}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)

# Prometheus metrics
CACHE_MISSES = Counter('cache_misses_total', 'Total number of cache misses')
CACHE_OPS = Counter('cache_operations_total', 'Cache operations', ['operation'])
CACHE_OP_DURATION = Histogram('cache_operation_duration_seconds', 'Time spent on cache operations', ['operation'])
PENDING_CACHES = Gauge('pending_caches', 'Number of files currently being cached')
CACHED_FILES = Gauge('cached_files_total', 'Total number of cached files')

cache_stats = {
    'pending_caches': set(),
    'cached_files': set()
}

async def analyze_miss_pattern(redis_client: redis.Redis, video_id: str, file_name: str) -> Tuple[int, List[str]]:
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
    object_path = f"hls/{video_id}/{file_name}"
    
    if (object_path in cache_stats['cached_files'] or 
        object_path in cache_stats['pending_caches']):
        return False
    
    miss_count, timestamps = await analyze_miss_pattern(redis_client, video_id, file_name)
    
    if miss_count < settings.min_miss_count:
        return False
        
    timestamps = [datetime.fromisoformat(ts) for ts in timestamps]
    recent_threshold = datetime.now() - timedelta(hours=settings.time_window_hours)
    recent_misses = [ts for ts in timestamps if ts > recent_threshold]
    
    return len(recent_misses) >= settings.min_miss_count

async def cache_file(video_id: str, file_name: str):
    object_path = f"hls/{video_id}/{file_name}"
    try:
        cache_stats['pending_caches'].add(object_path)
        PENDING_CACHES.inc()
        
        with CACHE_OP_DURATION.labels('transfer').time():
            data = minio_core_client.get_object(settings.core_bucket, object_path)
            minio_cache_client.put_object(
                settings.cache_bucket,
                object_path,
                data,
                length=-1,
                part_size=10*1024*1024
            )
        
        cache_stats['cached_files'].add(object_path)
        cache_stats['pending_caches'].remove(object_path)
        CACHED_FILES.inc()
        PENDING_CACHES.dec()
        CACHE_OPS.labels('success').inc()
        
    except Exception as e:
        logger.error(f"Error caching file {object_path}: {e}")
        cache_stats['pending_caches'].remove(object_path)
        PENDING_CACHES.dec()
        CACHE_OPS.labels('error').inc()
        raise

async def process_cache_miss(redis_client: redis.Redis, message: Dict):
    try:
        video_id = message.get('video_id')
        file_name = message.get('file_name')
        
        if not video_id or not file_name:
            logger.error(f"Invalid message format: {message}")
            CACHE_OPS.labels('invalid_message').inc()
            return
        
        CACHE_MISSES.inc()
        with CACHE_OP_DURATION.labels('process_miss').time():
            if await should_cache_file(redis_client, video_id, file_name):
                await cache_file(video_id, file_name)
            
    except Exception as e:
        logger.error(f"Error processing cache miss: {e}")
        CACHE_OPS.labels('error').inc()

async def redis_subscriber():
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True
    )
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(settings.redis_channel)
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
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
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )
        redis_client.ping()
        redis_client.close()
        
        asyncio.create_task(redis_subscriber())
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.get("/stats")
async def get_cache_stats():
    return {
        "pending_caches": list(cache_stats['pending_caches']),
        "cached_files": list(cache_stats['cached_files']),
        "pending_count": len(cache_stats['pending_caches']),
        "cached_count": len(cache_stats['cached_files'])
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)