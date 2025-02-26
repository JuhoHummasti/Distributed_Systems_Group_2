import grpc
import file_storage_service_pb2
import file_storage_service_pb2_grpc

def get_video_download_url(video_id):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = file_storage_service_pb2_grpc.FileStorageServiceStub(channel)
        request = file_storage_service_pb2.VideoDownloadUrlRequest(video_id=video_id)
        response = stub.GetVideoDownloadUrl(request)
        return response.download_url

if __name__ == '__main__':
    video_id = "1.mp4"
    download_url = get_video_download_url(video_id)
    print(f"Download URL: {download_url}")