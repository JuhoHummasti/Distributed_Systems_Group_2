import grpc
from concurrent import futures
import time
from minio import Minio
from minio.error import S3Error
import presigner_pb2
import presigner_pb2_grpc

class PresignerService(presigner_pb2_grpc.PresignerServiceServicer):
    def __init__(self):
        self.minio_client = Minio(
            "localhost:9000",
            access_key="myaccesskey",
            secret_key="mysecretkey",
            secure=False
        )
        self.bucket_name = "videos"
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)

    def GetVideoDownloadUrl(self, request, context):
        video_id = request.video_id
        url = self.minio_client.presigned_get_object(self.bucket_name, video_id)
        return presigner_pb2.VideoDownloadUrlResponse(download_url=url)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    presigner_pb2_grpc.add_PresignerServiceServicer_to_server(PresignerService(), server)
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