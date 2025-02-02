from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
import os
from pathlib import Path
import tempfile
import logging
import time
from typing import Optional
import subprocess
import asyncio
import shutil
from pydantic_settings import BaseSettings

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


@app.on_event("startup")
async def startup_event():
    """Initialize service"""
    try:
        if not minio_client.bucket_exists(settings.minio_bucket):
            minio_client.make_bucket(settings.minio_bucket)
            logger.info(f"Created bucket: {settings.minio_bucket}")
    except Exception as e:
        logger.error(f"Error creating bucket: {e}")
        raise

@app.get("/stream/{video_id}/playlist.m3u8")
async def get_playlist(video_id: str):
    """Get the HLS playlist file"""
    try:
        bucket_name = "cache"
        object_name = f"hls/{video_id}/playlist.m3u8"
        
        # Check if the object exists
        try:
            minio_client.stat_object(bucket_name, object_name)
        except Exception:
            raise HTTPException(status_code=404, detail="Playlist not found")
        
        # Retrieve the object
        response = minio_client.get_object(bucket_name, object_name)
        
        return StreamingResponse(
            response.stream(),
            media_type="application/vnd.apple.mpegurl",
            headers={"Content-Disposition": f"filename=playlist.m3u8"}
        ) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}/{segment_file}")
async def get_segment(video_id: str, segment_file: str):
    """Get individual HLS segment"""
    try:
        bucket_name = "cache"
        object_name = f"hls/{video_id}/{segment_file}"
        
        # Check if the object exists
        try:
            minio_client.stat_object(bucket_name, object_name)
        except Exception:
            raise HTTPException(status_code=404, detail="Segment not found")
        
        # Retrieve the object
        response = minio_client.get_object(bucket_name, object_name)
        
        return StreamingResponse(
            response.stream(), 
            media_type="video/MP2T",
            headers={"Content-Disposition": f"filename={segment_file}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MinIO connection
        minio_client.list_buckets()
        return {
            "status": "healthy",
            "minio_connection": "ok",
            "storage_path": str(VIDEOS_DIR),
            "storage_available": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@app.on_event("startup")
async def setup_cleanup():
    async def cleanup_old_files():
        while True:
            try:
                current_time = time.time()
                for item in VIDEOS_DIR.glob("*"):
                    if current_time - item.stat().st_mtime > settings.hls_max_age:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                        logger.info(f"Cleaned up {item}")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(settings.hls_cleanup_interval)
    
    asyncio.create_task(cleanup_old_files())