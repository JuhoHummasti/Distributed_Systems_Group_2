import asyncio
import grpc
from concurrent import futures
import streaming_pb2
import streaming_pb2_grpc
import os
from pathlib import Path
from aiohttp import web
import mimetypes

class StreamingService(streaming_pb2_grpc.StreamingServiceServicer):
    def __init__(self, node_id, video_dir="cache", http_port=8080):
        self.node_id = node_id
        self.video_dir = video_dir
        self.http_port = http_port
        Path(video_dir).mkdir(exist_ok=True)

    async def GetStream(self, request, context):
        try:
            video_id = request.video_id
            video_path = os.path.join(self.video_dir, f"{video_id}.mp4")
            
            if not os.path.exists(video_path):
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f'Video {video_id} not found')
                return streaming_pb2.StreamResponse()

            # Return HTTP URL instead of file URL
            stream_url = f"http://localhost:{self.http_port}/videos/{video_id}.mp4"
            return streaming_pb2.StreamResponse(
                stream_url=stream_url,
                edge_node_id=f"edge{self.node_id}"
            )
        except Exception as e:
            print(f"Error in GetStream: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            raise

    async def HealthCheck(self, request, context):
        try:
            return streaming_pb2.HealthResponse(status=True)
        except Exception as e:
            print(f"Error in HealthCheck: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            raise

async def handle_video_request(request):
    video_name = request.match_info['video_name']
    video_path = os.path.join('videos', video_name)
    
    if not os.path.exists(video_path):
        return web.Response(status=404, text="Video not found")

    return web.FileResponse(video_path)

async def run_http_server(port):
    app = web.Application()
    app.router.add_get('/videos/{video_name}', handle_video_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    print(f"HTTP server running on port {port}")

async def serve(grpc_port, node_id, http_port=8080):
    # Start HTTP server
    await run_http_server(http_port)
    
    # Start gRPC server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(
        StreamingService(node_id, http_port=http_port), server
    )
    listen_addr = f'[::]:{grpc_port}'
    server.add_insecure_port(listen_addr)
    print(f"gRPC server starting on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        print("Usage: python edge_node.py <port> <node_id>")
        sys.exit(1)
    
    port = sys.argv[1]
    node_id = sys.argv[2]
    http_port = sys.argv[3]
    
    asyncio.run(serve(port, node_id, http_port))