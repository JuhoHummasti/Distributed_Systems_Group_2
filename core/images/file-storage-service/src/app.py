import os
import grpc
from concurrent import futures
import time
from minio import Minio
from minio.error import S3Error
import file_storage_service_pb2
import file_storage_service_pb2_grpc

class FileStorageService(file_storage_service_pb2_grpc.FileStorageServiceServicer):
    def __init__(self):
        self.minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "myaccesskey"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "mysecretkey"),
            secure=False
        )
        self.bucket_name = "videos"
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)

    def GetVideoDownloadUrl(self, request, context):
        video_id = request.video_id
        url = self.minio_client.presigned_get_object(self.bucket_name, video_id)
        return file_storage_service_pb2.VideoDownloadUrlResponse(download_url=url)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    file_storage_service_pb2_grpc.add_FileStorageServiceServicer_to_server(FileStorageService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()