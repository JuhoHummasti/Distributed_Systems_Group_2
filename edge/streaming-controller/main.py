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
    minio_host: str = os.getenv("MINIO_HOST", "localhost")
    minio_port: str = os.getenv("MINIO_PORT", "9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "videos")
    
    # HLS settings
    hls_segment_duration: int = int(os.getenv("HLS_SEGMENT_DURATION", "10"))
    hls_cleanup_interval: int = int(os.getenv("HLS_CLEANUP_INTERVAL", "3600"))
    hls_max_age: int = int(os.getenv("HLS_MAX_AGE", "3600"))
    
    # Storage settings
    storage_path: str = os.getenv("STORAGE_PATH", "/tmp/hls_videos")
    
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

# Create storage directory
VIDEOS_DIR = Path(settings.storage_path)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

async def create_hls_stream(video_path: str, output_dir: Path) -> None:
    """Create HLS stream using ffmpeg subprocess"""
    output_dir.mkdir(exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-start_number', '0',
        '-hls_time', str(settings.hls_segment_duration),
        '-hls_list_size', '0',
        '-f', 'hls',
        str(output_dir / 'playlist.m3u8')
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        logger.error(f"FFmpeg error: {stderr.decode()}")
        raise Exception(f"FFmpeg failed with return code {process.returncode}")

async def get_video_path(video_id: str) -> Path:
    """Get or download video from MinIO"""
    video_path = VIDEOS_DIR / video_id
    hls_dir = VIDEOS_DIR / f"{video_id}_hls"
    
    if not video_path.exists():
        try:
            # Download from MinIO if not already downloaded
            await asyncio.to_thread(
                minio_client.fget_object,
                settings.minio_bucket,
                video_id,
                str(video_path)
            )
            logger.info(f"Downloaded video {video_id} from MinIO")
            
            # Create HLS stream
            await create_hls_stream(str(video_path), hls_dir)
            logger.info(f"Created HLS segments for {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to process video {video_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    if not (hls_dir / "playlist.m3u8").exists():
        try:
            await create_hls_stream(str(video_path), hls_dir)
        except Exception as e:
            logger.error(f"Failed to create HLS stream: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return hls_dir

@app.on_event("startup")
async def startup_event():
    """Initialize service"""
    logger.info("Starting HLS Streaming Service with configuration:")
    logger.info(f"MinIO Endpoint: {settings.minio_host}:{settings.minio_port}")
    logger.info(f"MinIO Bucket: {settings.minio_bucket}")
    logger.info(f"Storage Path: {settings.storage_path}")
    logger.info(f"HLS Segment Duration: {settings.hls_segment_duration}s")
    
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
        hls_dir = await get_video_path(video_id)
        playlist_path = hls_dir / "playlist.m3u8"
        return FileResponse(
            path=playlist_path,
            media_type="application/vnd.apple.mpegurl",
            filename="playlist.m3u8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/{video_id}/{segment_file}")
async def get_segment(video_id: str, segment_file: str):
    """Get individual HLS segment"""
    try:
        hls_dir = await get_video_path(video_id)
        segment_path = hls_dir / segment_file
        
        if not segment_path.exists():
            raise HTTPException(status_code=404, detail="Segment not found")
            
        return FileResponse(
            path=segment_path,
            media_type="video/MP2T",
            filename=segment_file
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