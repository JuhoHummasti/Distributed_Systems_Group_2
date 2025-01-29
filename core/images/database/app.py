from fastapi import FastAPI
from crud import router

app = FastAPI()

# Include the router
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI MongoDB Microservice!"}