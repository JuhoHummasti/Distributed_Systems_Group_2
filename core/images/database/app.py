from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from crud import router

app = FastAPI(title="Database crud service")

# Include the router
app.include_router(router, prefix="/api/v1")

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI MongoDB Microservice!"}