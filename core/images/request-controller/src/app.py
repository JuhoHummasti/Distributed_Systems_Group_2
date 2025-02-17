from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import requests
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import grpc
import file_storage_service_pb2
import file_storage_service_pb2_grpc
from typing import List, Dict
import httpx
import os
from pydantic import BaseModel

app = FastAPI(title="Video Request Controller")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Get database service URL from environment variable
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:8011")
FILE_STORAGE_SERVICE_URL = "file-storage-service:50051"

async def get_thumbnail_urls(video_ids: List[str]) -> Dict[str, str]:
    # Create gRPC channel and client
    channel = grpc.aio.insecure_channel(FILE_STORAGE_SERVICE_URL)
    stub = file_storage_service_pb2_grpc.FileStorageServiceStub(channel)
    
    # Create the batch request with thumbnail paths
    thumbnail_paths = [f"thumbnails/{video_id}.jpg" for video_id in video_ids]
    request = file_storage_service_pb2.BatchVideoDownloadUrlRequest(video_ids=thumbnail_paths)
    
    try:
        # Make the gRPC call
        response = await stub.GetBatchVideoDownloadUrls(request)
        await channel.close()
        return response.download_urls
    except grpc.RpcError as e:
        await channel.close()
        raise HTTPException(status_code=503, detail="File storage service unavailable")

@app.get("/videos")
async def get_all_videos():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DATABASE_SERVICE_URL}/api/v1/items/")
            response.raise_for_status()
            videos = response.json()
            
            if not videos:
                return []
            
            # Extract video IDs
            video_ids = [video["video_id"] for video in videos]
            
            # Get thumbnail URLs
            thumbnail_urls = await get_thumbnail_urls(video_ids)
            
            # Add thumbnail URLs to video data
            for video in videos:
                thumbnail_path = f"thumbnails/{video['video_id']}.jpg"
                video["thumbnail_url"] = thumbnail_urls.get(thumbnail_path, "")
            
            return videos
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/videos/{video_id}")
async def get_video(video_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DATABASE_SERVICE_URL}/api/v1/items/videos?filter={{'video_id':'{video_id}'}}")            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Video not found")
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/serve")
async def serve_minio_file(url: str):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return StreamingResponse(
            response.iter_content(chunk_size=8192), 
            media_type=response.headers.get('Content-Type', 'application/octet-stream')
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    
@app.get("/health")
async def health_check():
    return {"status": "healthy"}