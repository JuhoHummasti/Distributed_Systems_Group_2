from fastapi import FastAPI, HTTPException
from typing import List
import httpx
import os
from pydantic import BaseModel

app = FastAPI(title="Video Request Controller")

# Get database service URL from environment variable
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:8011")

@app.get("/videos")
async def get_all_videos():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DATABASE_SERVICE_URL}/items")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/video/{video_id}")
async def get_video(video_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{DATABASE_SERVICE_URL}/items/{video_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Video not found")
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}