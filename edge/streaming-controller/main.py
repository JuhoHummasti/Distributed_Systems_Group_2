from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from minio.error import S3Error
import os
import io
from pathlib import Path
import tempfile
import logging
import time
from typing import Optional
import subprocess
import asyncio
import shutil
from pydantic_settings import BaseSettings
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

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
            
            # If exists, stream from local cache
            response = minio_client.get_object(bucket_name, object_name)
            return StreamingResponse(
                response.stream(),
                media_type="application/vnd.apple.mpegurl",
                headers={"Content-Disposition": f"filename=playlist.m3u8"}
            )
        except Exception as local_err:
            CACHE_MISSES.inc()
            print(f"Error checking local cache: {local_err}")
            
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
            # If exists, stream from local cache
            response = minio_client.get_object(bucket_name, object_name)
            return StreamingResponse(
                response.stream(), 
                media_type="video/MP2T",
                headers={"Content-Disposition": f"filename={segment_file}"}
            )
        except Exception:
            CACHE_MISSES.inc()
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