import os
import grpc
from concurrent import futures
import time
from minio import Minio
from minio.error import S3Error
import file_storage_service_pb2
import file_storage_service_pb2_grpc

from prometheus_client import make_wsgi_app, Counter, Histogram

from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

from threading import Thread

REQUEST_COUNT = Counter('file_storage_service_requests_total', 'Total number of requests')
SUCCESS_COUNT = Counter('file_storage_service_success_total', 'Total number of successful requests')
ERROR_COUNT = Counter('file_storage_service_errors_total', 'Total number of errors')
REQUEST_LATENCY = Histogram('file_storage_service_request_latency_seconds', 'Request latency in seconds')


class FileStorageService(file_storage_service_pb2_grpc.FileStorageServiceServicer):
    def __init__(self):
        self.minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "nginx:7010"),
            access_key=os.getenv("MINIO_ROOT_USER", "myaccesskey"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "mysecretkey"),
            secure=False
        )
        self.bucket_name = "videos"
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)
    
    def replace_hostname(self, url: str) -> str:
        """Replace nginx:7010 with localhost:7010 in the presigned URL."""
        return url.replace("nginx:7010", "localhost:7010")

    @REQUEST_LATENCY.time()
    def GetVideoDownloadUrl(self, request, context):
        REQUEST_COUNT.inc()
        try:
            video_id = request.video_id
            url = self.minio_client.presigned_get_object(self.bucket_name, video_id)
            url = self.replace_hostname(url)
            SUCCESS_COUNT.inc()
            return file_storage_service_pb2.VideoDownloadUrlResponse(download_url=url)
        except Exception as e:
            ERROR_COUNT.inc()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return file_storage_service_pb2.VideoDownloadUrlResponse()

    @REQUEST_LATENCY.time()
    def GetBatchVideoDownloadUrls(self, request, context):
        REQUEST_COUNT.inc()
        try:
            urls = {}
            for video_id in request.video_ids:
                try:
                    url = self.minio_client.presigned_get_object(self.bucket_name, video_id)
                    url = self.replace_hostname(url)
                    urls[video_id] = url
                except Exception as e:
                    # Log the error but continue processing other files
                    print(f"Error generating URL for {video_id}: {str(e)}")
                    urls[video_id] = ""
            
            SUCCESS_COUNT.inc()
            return file_storage_service_pb2.BatchVideoDownloadUrlResponse(download_urls=urls)
        except Exception as e:
            ERROR_COUNT.inc()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return file_storage_service_pb2.BatchVideoDownloadUrlResponse()


# Replace the serve_metrics function with:
def serve_metrics():
    metrics_app = make_wsgi_app()
    
    def router(environ, start_response):
        setup_testing_defaults(environ)
        if environ['PATH_INFO'] == '/metrics':
            return metrics_app(environ, start_response)
        
        # Return 404 for other paths
        status = '404 Not Found'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'Not Found']

    httpd = make_server('', 8000, router)
    httpd.serve_forever()

def serve():
        # Start the Prometheus metrics server in a separate thread
    metrics_thread = Thread(target=serve_metrics)
    metrics_thread.start()
    
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