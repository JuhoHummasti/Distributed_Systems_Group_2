import unittest
import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import hashlib
import os
from tqdm import tqdm

class VideoStorageTest(unittest.TestCase):
    API_URL = "http://localhost:8000"
    VIDEO_PATH = "videos/test_5gb"
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks

    def setUp(self):
        self.downloaded_file = 'downloaded_video.mp4'
        
    def tearDown(self):
        if os.path.exists(self.downloaded_file):
            os.remove(self.downloaded_file)

    def create_callback(self, pbar):
        def callback(monitor):
            pbar.update(monitor.bytes_read - pbar.n)
        return callback

    def test_upload_download(self):
        print("\n=== Starting Video Upload/Download Test ===")
        
        # Upload video
        print(f"\nUploading video from {self.VIDEO_PATH}...")
        total_size = os.path.getsize(self.VIDEO_PATH)
        
        with open(self.VIDEO_PATH, 'rb') as f:
            encoder = MultipartEncoder({
                'file': ('video.mp4', f, 'video/mp4')
            })
            
            with tqdm(total=total_size, desc="Uploading", unit='B', unit_scale=True) as pbar:
                monitor = MultipartEncoderMonitor(encoder, self.create_callback(pbar))
                
                response = requests.post(
                    f"{self.API_URL}/upload/",
                    data=monitor,
                    headers={'Content-Type': monitor.content_type}
                )
        
        self.assertEqual(response.status_code, 200)
        video_id = response.json()['id']
        print(f"Upload successful! Video ID: {video_id}")
        
        # Download video
        print(f"\nDownloading video with ID: {video_id}...")
        with requests.get(f"{self.API_URL}/video/{video_id}", stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with tqdm(total=total_size, desc="Downloading", unit='B', unit_scale=True) as pbar:
                with open(self.downloaded_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=self.CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        # Compare files using generators
        print("\nComparing file hashes...")
        original_hash = self._hash_file(self.VIDEO_PATH)
        downloaded_hash = self._hash_file(self.downloaded_file)
        
        self.assertEqual(original_hash, downloaded_hash)
        print("File comparison successful - hashes match!")

    # def test_list_videos(self):
    #     print("\n=== Starting List Videos Test ===")
        
    #     # Test empty list
    #     response = requests.get(f"{self.API_URL}/videos/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.json()), 0)
    #     print("Empty list test passed")
        
    #     # Upload a video for testing
    #     with open(self.VIDEO_PATH, 'rb') as f:
    #         encoder = MultipartEncoder({
    #             'file': ('video.mp4', f, 'video/mp4')
    #         })
    #         response = requests.post(
    #             f"{self.API_URL}/upload/",
    #             data=encoder,
    #             headers={'Content-Type': encoder.content_type}
    #         )
    #     self.assertEqual(response.status_code, 200)
    #     uploaded_id = response.json()['id']
        
    #     # Test list with video
    #     response = requests.get(f"{self.API_URL}/videos/")
    #     self.assertEqual(response.status_code, 200)
    #     videos = response.json()
    #     self.assertEqual(len(videos), 1)
    #     self.assertEqual(videos[0]['id'], uploaded_id)
    #     print("List with video test passed")

    def test_delete_video(self):
        print("\n=== Starting Delete Video Test ===")
        
        # Upload a video for testing
        with open(self.VIDEO_PATH, 'rb') as f:
            encoder = MultipartEncoder({
                'file': ('video.mp4', f, 'video/mp4')
            })
            response = requests.post(
                f"{self.API_URL}/upload/",
                data=encoder,
                headers={'Content-Type': encoder.content_type}
            )
        self.assertEqual(response.status_code, 200)
        video_id = response.json()['id']
        
        # Test successful deletion
        response = requests.delete(f"{self.API_URL}/video/{video_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], "Video deleted successfully")
        print("Delete video test passed")

    def _hash_file(self, filepath):
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(self.CHUNK_SIZE):
                md5.update(chunk)
                del chunk
        return md5.hexdigest()

if __name__ == '__main__':
    unittest.main()