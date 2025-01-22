from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from utils.validators import validate_video_file, generate_unique_id
from utils.video_storage import VideoStorage
import os

app = FastAPI()
video_storage = VideoStorage()

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")
    if not validate_video_file(file):
        raise HTTPException(status_code=400, detail="Invalid video file format")

    video_id = generate_unique_id()
    video_storage.save_video(file.file, video_id)
    return JSONResponse(content={"message": "File uploaded successfully", "video_id": video_id}, status_code=201)

@app.get("/video/{video_id}")
async def get_video(video_id: str):
    video = video_storage.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video, media_type='application/octet-stream', filename=os.path.basename(video))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)