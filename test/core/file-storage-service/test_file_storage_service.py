import pytest
import grpc
import file_storage_service_pb2
import file_storage_service_pb2_grpc

@pytest.fixture(scope="module")
def grpc_channel():
    channel = grpc.insecure_channel('localhost:50051')
    yield channel
    channel.close()

@pytest.fixture(scope="module")
def grpc_stub(grpc_channel):
    return file_storage_service_pb2_grpc.FileStorageServiceStub(grpc_channel)

def test_get_video_download_url(grpc_stub):
    # Test case for GetVideoDownloadUrl method
    request = file_storage_service_pb2.VideoDownloadUrlRequest(video_id='00e59669-a16a-4bce-8558-8e23bc087f58')
    response = grpc_stub.GetVideoDownloadUrl(request)
    assert response.download_url is not None
    assert response.download_url.startswith('http')

if __name__ == '__main__':
    pytest.main()