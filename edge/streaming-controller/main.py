from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error
import redis
from datetime import datetime
import json
import os
import logging
from pydantic import validator
from pydantic_settings import BaseSettings
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from confluent_kafka import Producer

# Custom metrics
CACHE_HITS = Counter(
    'streaming_cache_hits_total',
    'Number of cache hits when retrieving video segments'
)
CACHE_MISSES = Counter(
    'streaming_cache_misses_total',
    'Number of cache misses when retrieving video segments'
)
SEGMENT_RETRIEVAL_TIME = Histogram(
    'streaming_segment_retrieval_seconds',
    'Time spent retrieving video segments',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)
MINIO_CONNECTION_STATUS = Gauge(
    'streaming_minio_connection_status',
    'MinIO connection status (1 for connected, 0 for disconnected)'
)

class Settings(BaseSettings):
    # MinIO settings
    minio_host: str = os.getenv("MINIO_HOST", "minio")
    minio_port: str = os.getenv("MINIO_PORT", "9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "videos")

    # Redis settings
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: str = os.getenv("REDIS_PORT", "6379")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_channel: str = os.getenv("REDIS_CHANNEL", "cache_misses")

    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    kafka_topic: str = os.getenv("KAFKA_TOPIC", "cache_missed")

    @validator('redis_port')
    def parse_redis_port(cls, v):
        if ":" in v:
            return int(v.split(":")[-1])
        return int(v)
    
    class Config:
        env_file = ".env"

settings = Settings()
app = FastAPI(title="HLS Streaming Service")

# Initialize Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO client configuration
minio_client = Minio(
    f"{settings.minio_host}:{settings.minio_port}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)

# MinIO client configuration
minio_client_core = Minio(
    f"{os.getenv('MINIO_HOST_CORE', 'host.docker.internal')}:{os.getenv('MINIO_PORT_CORE', '7010')}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False
)

# Initialize Redis client
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)

kafka_producer = Producer({
    'bootstrap.servers': settings.kafka_bootstrap_servers,
    'api.version.request': True
})

def log_file_request(video_id: str, file_name: str, cache_hit: bool):
    """Log file request metrics to Redis with complete filename"""
    timestamp = datetime.now().isoformat()
    full_path = f"{video_id}/{file_name}"
    
    # Determine the key based on hit/miss
    key = f"hit:{full_path}" if cache_hit else f"missed:{full_path}"
    
    # Check if the key exists
    if not redis_client.exists(key):
        # Initialize new record
        initial_data = {
            "count": 1,
            "timestamps": [timestamp]
        }
        redis_client.set(key, json.dumps(initial_data))
    else:
        # Update existing record
        current_data = json.loads(redis_client.get(key))
        current_data["count"] += 1
        current_data["timestamps"].append(timestamp)
        redis_client.set(key, json.dumps(current_data))

    if not cache_hit:
        # Prepare cache miss event
        event = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "file_name": file_name,
            "event_type": "cache_miss"
        }
        
        # Publish to Redis channel
        redis_client.publish(
            settings.redis_channel,
            json.dumps(event)
        )
        logger.info(f"Published cache miss event for {video_id}/{file_name}")

def send_cache_miss_event(video_id: str, file_name: str):
    """Send cache miss event to Kafka"""
    try:
        message = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "file_name": file_name,
            "event_type": "cache_miss"
        }
        
        # Serialize the message to bytes
        value = json.dumps(message).encode('utf-8')
        
        # Define delivery callback
        def delivery_callback(err, msg):
            if err:
                logger.error(f'Message delivery failed: {err}')
            else:
                logger.debug(f'Message delivered to {msg.topic()}')
        
        # Produce the message
        kafka_producer.produce(
            topic=settings.kafka_topic,
            value=value,
            callback=delivery_callback
        )
        
        # Flush to ensure the message is sent
        kafka_producer.poll(0)  # Trigger any callbacks
        
        logger.info(f"Sent cache miss event to Kafka: {message}")
    except Exception as e:
        logger.error(f"Failed to send cache miss event to Kafka: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize service"""
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            logger.info(f"Created bucket: {settings.minio_bucket}")
        MINIO_CONNECTION_STATUS.set(1)
    except Exception as e:
        logger.error(f"Error creating bucket: {e}")
        MINIO_CONNECTION_STATUS.set(0)
        raise

@app.get("/stream/{video_id}/playlist.m3u8")
async def get_playlist(video_id: str):
    """Get the HLS playlist file, retrieving from core storage if not in cache"""
    try:
        bucket_name = "cache"
        core_bucket_name = "videos"
        object_name = f"hls/{video_id}/playlist.m3u8"
        
        # First, check if the object exists in the local cache
        try:
            # Attempt to stat the object
            minio_client.stat_object(bucket_name, object_name)
            CACHE_HITS.inc()
            log_file_request(video_id, "playlist.m3u8", True)  # Log cache hit
            
            # If exists, stream from local cache
            response = minio_client.get_object(bucket_name, object_name)
            return StreamingResponse(
                response.stream(),
                media_type="application/vnd.apple.mpegurl",
                headers={"Content-Disposition": f"filename=playlist.m3u8"}
            )
        except Exception as local_err:
            CACHE_MISSES.inc()
            log_file_request(video_id, "playlist.m3u8", False)  # Log cache miss
            send_cache_miss_event(video_id, "playlist.m3u8")
            
            # If not in local cache, try to retrieve from core storage
            try:
                with SEGMENT_RETRIEVAL_TIME.time():
                    # Check if object exists in core storage
                    minio_client_core.stat_object(core_bucket_name, object_name)
                    
                    # Retrieve object from core storage
                    response = minio_client_core.get_object(core_bucket_name, object_name)
                    
                    # Return StreamingResponse
                    return StreamingResponse(
                        response.stream(),
                        media_type="application/vnd.apple.mpegurl",
                        headers={"Content-Disposition": f"filename=playlist.m3u8"}
                    )
            except Exception as core_err:
                # If not found in either location
                print(f"Error retrieving from core storage: {core_err}")
                raise HTTPException(status_code=404, detail=f"Playlist not found: {core_err}")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}/{segment_file}")
async def get_segment(video_id: str, segment_file: str):
    """Get individual HLS segment, retrieving from core storage if not in cache"""
    try:
        bucket_name = "cache"
        core_bucket_name = "videos"
        object_name = f"hls/{video_id}/{segment_file}"
        
        # First, check if the object exists in the local cache
        try:
            minio_client.stat_object(bucket_name, object_name)
            CACHE_HITS.inc()            
            log_file_request(video_id, segment_file, True)  # Log cache hit

            # If exists, stream from local cache
            response = minio_client.get_object(bucket_name, object_name)
            return StreamingResponse(
                response.stream(), 
                media_type="video/MP2T",
                headers={"Content-Disposition": f"filename={segment_file}"}
            )
        except Exception:
            CACHE_MISSES.inc()
            log_file_request(video_id, segment_file, False)  # Log cache miss
            send_cache_miss_event(video_id, segment_file)

            # If not in local cache, try to retrieve from core storage
            try:
                with SEGMENT_RETRIEVAL_TIME.time():
                    # Check if object exists in core storage
                    minio_client_core.stat_object(core_bucket_name, object_name)
                    
                    # Retrieve object from core storage
                    response = minio_client_core.get_object(core_bucket_name, object_name)
                    # Return StreamingResponse
                    return StreamingResponse(
                        response.stream(),
                        media_type="video/MP2T",
                        headers={"Content-Disposition": f"filename={segment_file}"}
                    )
            except Exception as core_err:
                print(f"Detailed error: {core_err}")
                print(f"Error type: {type(core_err)}")
                # If not found in either location
                raise HTTPException(status_code=404, detail="Segment not found")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    kafka_producer.close()
    logger.info("Kafka producer closed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MinIO connection
        minio_client.list_buckets()
        MINIO_CONNECTION_STATUS.set(1)
        return {
            "status": "healthy",
            "minio_connection": "ok",
            "storage_available": True
        }
    except Exception as e:
        MINIO_CONNECTION_STATUS.set(0)
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )