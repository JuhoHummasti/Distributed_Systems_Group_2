import pytest
import grpc
import file_storage_service_pb2
import file_storage_service_pb2_grpc


import sys
from pathlib import Path

# Add test directory to Python path
test_dir = str(Path(__file__).parent.parent.parent)
if test_dir not in sys.path:
    sys.path.append(test_dir)

from utils.port_forward import PortForwarder

@pytest.fixture(scope="session", autouse=True)
def port_forwarder():
    forwarder = PortForwarder()
    # Add all required services
    #forwarder.start_port_forward("video-uploader", 8000, 8000)
    #forwarder.start_port_forward("database-service", 8011, 8011)
    forwarder.start_port_forward("file-storage-service", 50051, 50051)
    #forwarder.start_port_forward("minio", 9000, 9000)
    
    yield forwarder
    
    forwarder.cleanup()

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