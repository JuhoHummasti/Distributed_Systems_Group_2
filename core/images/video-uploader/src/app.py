import logging
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from minio import Minio
from minio.error import S3Error
from confluent_kafka import Producer
import os
import uuid
import json
import uvicorn
import tempfile
import httpx
from typing import List
from pydantic import BaseModel
from datetime import datetime, timezone
from profiler_middleware import ProfilerMiddleware
from process_video import VideoProcessor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()
video_processor = VideoProcessor()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add the profiler middleware if enabled
if os.getenv("ENABLE_PROFILER") == "1":
    app.add_middleware(ProfilerMiddleware)

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Minio configuration using environment variables
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ROOT_USER", "myaccesskey"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "mysecretkey"),
    secure=False
)

# Kafka configuration using environment variables
kafka_conf = {
    'bootstrap.servers': os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    'client.id': 'video_storage',
}

# Create a Producer instance
producer = Producer(kafka_conf)

CHUNK_SIZE = 1024 * 1024  # 1MB chunks
BUCKET_NAME = "videos"

class VideoMetadata(BaseModel):
    filename: str
    size: int
    id: str

# Ensure bucket exists
if not minio_client.bucket_exists(BUCKET_NAME):
    minio_client.make_bucket(BUCKET_NAME)

def send_kafka_message(topic, message):
    def delivery_report(err, msg):
        if err is not None:
            print(f"Message delivery failed: {err}")
        else:
            print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    producer.produce(topic, json.dumps(message).encode('utf-8'), callback=delivery_report)

@app.post("/upload/", response_model=VideoMetadata)
async def upload_video(file: UploadFile, background_tasks: BackgroundTasks):
    try:
        logger.debug("Received upload request for file: %s", file.filename)
        video_id = str(uuid.uuid4())
        
        # Save uploaded file with proper extension
        original_extension = os.path.splitext(file.filename)[1]
        temp_path = os.path.join(
            tempfile.gettempdir(), 
            f"upload_{video_id}{original_extension}"
        )
        
        # Write to temp file first
        with open(temp_path, "wb") as temp_file:
            chunk_size = 1024 * 1024  # 1MB chunks
            while chunk := await file.read(chunk_size):
                temp_file.write(chunk)
        
        # Now upload to MinIO from the temp file
        with open(temp_path, "rb") as temp_file:
            file_size = os.path.getsize(temp_path)
            minio_client.put_object(
                bucket_name=BUCKET_NAME,
                object_name=video_id,
                data=temp_file,
                length=file_size,
                content_type=file.content_type
            )
        
        message = {
            "event": "upload",
            "video_id": video_id,
            "filename": file.filename,
            "size": file_size,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        send_kafka_message("video-uploads", message)
        
        # Store video metadata in database service
        item_data = {
            "video_id": video_id,
            "status": "processing",
            "title": file.filename,
            "time_created": datetime.utcnow().isoformat(),
            "time_updated": None
        }

        # Store video ID in database service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://database-service:8011/api/v1/items/",
                json=item_data
            )
            if response.status_code != 201:
                raise HTTPException(status_code=500, detail="Failed to store video metadata")
        
        # Start processing in the background
        video_processor.start_processing(video_id, temp_path)
        
        logger.debug("Uploaded file: %s with ID: %s", file.filename, video_id)
        return VideoMetadata(
            filename=file.filename,
            size=file_size,
            id=video_id
        )
        
    except Exception as e:
        logger.error("Error during upload: %s", e)
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/{video_id}")
async def get_video(video_id: str):
    try:
        logger.debug("Received download request for video ID: %s", video_id)
        response = minio_client.get_object(BUCKET_NAME, video_id)
        
        def iterfile():
            try:
                while True:
                    data = response.read(CHUNK_SIZE)
                    if not data:
                        break
                    yield data
            finally:
                response.close()
                response.release_conn()
        
        logger.debug("Streaming video ID: %s", video_id)
        return StreamingResponse(
            iterfile(),
            media_type="video/mp4"
        )
        
    except Exception as e:
        logger.error("Error during video retrieval: %s", e)
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/video/{video_id}/status")
async def get_video_status(video_id: str):
    """Get the current status of video processing"""
    status = await video_processor.get_processing_status(video_id)
    return {"video_id": video_id, "status": status}

@app.get("/videos/", response_model=List[VideoMetadata])
async def list_videos():
    try:
        logger.debug("Received request to list videos")
        videos = []
        objects = minio_client.list_objects(BUCKET_NAME)
        for obj in objects:
            videos.append(
                VideoMetadata(
                    filename=obj.object_name,
                    size=obj.size,
                    id=obj.object_name
                )
            )
        
        message = {
            "event": "list",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        send_kafka_message("video-list-attempts", message)
        
        logger.debug("Listed %d videos", len(videos))
        return videos
    except Exception as e:
        logger.error("Error listing videos: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/video/{video_id}")
async def delete_video(video_id: str):
    try:
        logger.debug("Received delete request for video ID: %s", video_id)
        minio_client.remove_object(BUCKET_NAME, video_id)
        
        message = {
            "event": "delete",
            "video_id": video_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        send_kafka_message("video-deletes", message)
        
        logger.debug("Deleted video ID: %s", video_id)
        return {"message": "Video deleted successfully"}
    except Exception as e:
        logger.error("Error deleting video: %s", e)
        raise HTTPException(status_code=404, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting video uploader service")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")