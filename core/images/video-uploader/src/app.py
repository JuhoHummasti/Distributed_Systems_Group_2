import logging
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.error import S3Error
from confluent_kafka import Producer
import os
import uuid
import json
import uvicorn
from typing import List
from pydantic import BaseModel
from datetime import datetime, timezone
from profiler_middleware import ProfilerMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add the profiler middleware if enabled
if os.getenv("ENABLE_PROFILER") == "1":
    app.add_middleware(ProfilerMiddleware)

# Minio configuration using environment variables
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
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
async def upload_video(file: UploadFile):
    try:
        logger.debug("Received upload request for file: %s", file.filename)
        video_id = str(uuid.uuid4())
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        minio_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=video_id,
            data=file.file,
            length=size,
            content_type=file.content_type
        )
        
        message = {
            "event": "upload",
            "video_id": video_id,
            "filename": file.filename,
            "size": size,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        send_kafka_message("video-uploads", message)
        
        logger.debug("Uploaded file: %s with ID: %s", file.filename, video_id)
        return VideoMetadata(
            filename=file.filename,
            size=size,
            id=video_id
        )
        
    except Exception as e:
        logger.error("Error during upload: %s", e)
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
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")