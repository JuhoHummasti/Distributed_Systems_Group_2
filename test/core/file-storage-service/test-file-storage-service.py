import unittest
import grpc
import file_storage_service_pb2
import file_storage_service_pb2_grpc

class TestFileStorageService(unittest.TestCase):
    def setUp(self):
        # Connect to the gRPC server
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = file_storage_service_pb2_grpc.FileStorageServiceStub(self.channel)

    def tearDown(self):
        # Close the gRPC channel
        self.channel.close()

    def test_get_video_download_url(self):
        # Test case for GetVideoDownloadUrl method
        request = file_storage_service_pb2.VideoDownloadUrlRequest(video_id='00e59669-a16a-4bce-8558-8e23bc087f58')
        response = self.stub.GetVideoDownloadUrl(request)
        self.assertIsNotNone(response.download_url)
        self.assertTrue(response.download_url.startswith('http'))

if __name__ == '__main__':
    unittest.main()