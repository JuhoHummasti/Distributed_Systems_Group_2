import unittest
import grpc
import video_file_pb2
import video_file_pb2_grpc
import tempfile
import os
import time
import subprocess

class VideoServiceTestCase(unittest.TestCase):
    def setUp(self):
        # Start the application with subprocess
        self.server_process = subprocess.Popen(['python', 'app.py'])
        time.sleep(5)  # Wait for the server to start

        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = video_file_pb2_grpc.VideoServiceStub(self.channel)
        self.upload_file_path = 'test/videos/testvideo.mp4'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.download_file_path = os.path.join(self.temp_dir.name, 'downloaded_testvideo.mp4')
        # self.large_video_path = self.save_large_file_to_temp(size_in_gb=5)

    def tearDown(self):
        self.channel.close()
        self.temp_dir.cleanup()

        # Stop the application
        self.server_process.terminate()
        self.server_process.wait()

    def save_large_file_to_temp(self, size_in_gb):
        file_path = os.path.join(self.temp_dir.name, 'large_test_file.tmp')
        
        with open(file_path, 'wb') as f:
            f.seek(size_in_gb * 1024 * 1024 * 1024 - 1)
            f.write(b'\0')
        
        return file_path

    def test_upload_and_download_video(self):
        # Upload video
        response = self.upload_video(self.upload_file_path)
        self.assertIsNotNone(response)
        self.assertTrue(hasattr(response, 'video_id'))
        print(f"Uploaded video with ID: {response.video_id}")

        # Download video
        self.download_video(response.video_id, self.download_file_path)
        print(f"Downloaded video to: {self.download_file_path}")

    """     def test_throughput(self):
        # Measure upload throughput
        start_time = time.time()
        response = self.upload_video(self.large_video_path)
        upload_time = time.time() - start_time
        self.assertIsNotNone(response)
        self.assertTrue(hasattr(response, 'video_id'))
        upload_file_size = os.path.getsize(self.large_video_path)
        upload_throughput = upload_file_size / upload_time
        print(f"Upload throughput: {upload_throughput / (1024 * 1024):.2f} MB/s")

        # Measure download throughput
        start_time = time.time()
        self.download_video(response.video_id, self.download_file_path)
        download_time = time.time() - start_time
        download_file_size = os.path.getsize(self.download_file_path)
        download_throughput = download_file_size / download_time
        print(f"Download throughput: {download_throughput / (1024 * 1024):.2f} MB/s")
    """

    def test_download_1Gb_video(self):
        # The large file is already uploaded to server with id test_2
        start_time = time.time()
        download_video_path = os.path.join(self.temp_dir.name, 'downloaded_large_test_file.tmp')
        self.download_video('test_2', download_video_path)
        download_time = time.time() - start_time
        download_file_size = os.path.getsize(download_video_path)
        download_throughput = download_file_size / download_time
        print(f"Download throughput: {download_throughput / (1024 * 1024):.2f} MB/s")

    def test_download_5Gb_video(self):
        # The large file is already uploaded to server with id test_5gb
        start_time = time.time()
        download_video_path = os.path.join(self.temp_dir.name, 'downloaded_large_test_file.tmp')
        self.download_video('test_5gb', download_video_path)
        download_time = time.time() - start_time
        download_file_size = os.path.getsize(download_video_path)
        download_throughput = download_file_size / download_time
        print(f"Download throughput: {download_throughput / (1024 * 1024):.2f} MB/s")

    def test_upload_1Gb_video(self):
        # Create a 1GB test file
        upload_file_path = self.save_large_file_to_temp(size_in_gb=1)
        
        start_time = time.time()
        response = self.upload_video(upload_file_path)
        upload_time = time.time() - start_time
        upload_file_size = os.path.getsize(upload_file_path)
        upload_throughput = upload_file_size / upload_time
        print(f"Upload throughput: {upload_throughput / (1024 * 1024):.2f} MB/s")

    def test_upload_5Gb_video(self):
        # Create a 5GB test file
        upload_file_path = self.save_large_file_to_temp(size_in_gb=5)
        
        start_time = time.time()
        response = self.upload_video(upload_file_path)
        upload_time = time.time() - start_time
        upload_file_size = os.path.getsize(upload_file_path)
        upload_throughput = upload_file_size / upload_time
        print(f"Upload throughput: {upload_throughput / (1024 * 1024):.2f} MB/s")

    def upload_video(self, file_path):
        def video_chunks():
            with open(file_path, 'rb') as f:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    yield video_file_pb2.VideoChunk(content=chunk)

        response = self.stub.UploadVideo(video_chunks())
        return response

    def download_video(self, video_id, output_path):
        request = video_file_pb2.VideoRequest(video_id=video_id)
        with open(output_path, 'wb') as f:
            for chunk in self.stub.DownloadVideo(request):
                f.write(chunk.content)

if __name__ == '__main__':
    unittest.main()