import grpc
from concurrent import futures
import video_file_pb2
import video_file_pb2_grpc
import os

from utils.validators import validate_video_file, generate_unique_id

class VideoService(video_file_pb2_grpc.VideoServiceServicer):
    def __init__(self, storage_dir='videos'):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def UploadVideo(self, request_iterator, context):
        video_id = generate_unique_id()
        file_path = os.path.join(self.storage_dir, video_id)
        with open(file_path, 'wb') as f:
            for chunk in request_iterator:
                f.write(chunk.content)
        return video_file_pb2.UploadResponse(video_id=video_id)

    def DownloadVideo(self, request, context):
        file_path = os.path.join(self.storage_dir, request.video_id)
        if not os.path.exists(file_path):
            context.abort(grpc.StatusCode.NOT_FOUND, "Video not found")
        with open(file_path, 'rb') as f:
            while chunk := f.read(1024 * 1024):  # 1MB chunks
                yield video_file_pb2.VideoChunk(content=chunk)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    video_file_pb2_grpc.add_VideoServiceServicer_to_server(VideoService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()