from fastapi import FastAPI, HTTPException
from typing import List
import grpc
import asyncio
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import streaming_pb2
import streaming_pb2_grpc

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EdgeNode(BaseModel):
    id: str
    address: str  # gRPC address (e.g., "localhost:50051")
    healthy: bool = True

class LoadBalancer:
    def __init__(self):
        # Initialize with edge nodes
        self.nodes: List[EdgeNode] = [
            EdgeNode(id="edge1", address="localhost:50051"),
            EdgeNode(id="edge2", address="localhost:50052"),
            EdgeNode(id="edge3", address="localhost:50053")
        ]
        self.current = 0
        
    async def get_next_node(self) -> EdgeNode:
        healthy_nodes = [node for node in self.nodes if node.healthy]
        if not healthy_nodes:
            raise HTTPException(status_code=503, detail="No healthy nodes available")
        
        selected = healthy_nodes[self.current % len(healthy_nodes)]
        self.current = (self.current + 1) % len(healthy_nodes)
        return selected

    async def health_check(self):
        for node in self.nodes:
            try:
                async with grpc.aio.insecure_channel(node.address) as channel:
                    stub = streaming_pb2_grpc.StreamingServiceStub(channel)
                    request = streaming_pb2.HealthRequest()
                    response = await stub.HealthCheck(request, timeout=2.0)
                    node.healthy = response.status
            except Exception as e:
                print(f"Health check failed for node {node.id}: {str(e)}")
                node.healthy = False

# Create load balancer instance
lb = LoadBalancer()

@app.get("/stream/{video_id}")
async def route_request(video_id: str):
    try:
        print("video streaming request for id", video_id)
        node = await lb.get_next_node()
        
        # Make gRPC call to edge node
        async with grpc.aio.insecure_channel(node.address) as channel:
            stub = streaming_pb2_grpc.StreamingServiceStub(channel)
            request = streaming_pb2.StreamRequest(video_id=video_id)
            response = await stub.GetStream(request)
            
            return {
                "stream_url": response.stream_url,
                "edge_node_id": response.edge_node_id
            }
            
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=f"gRPC error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Periodic health checks
@app.on_event("startup")
async def startup_event():
    async def periodic_health_check():
        while True:
            await lb.health_check()
            await asyncio.sleep(10)
    
    asyncio.create_task(periodic_health_check())