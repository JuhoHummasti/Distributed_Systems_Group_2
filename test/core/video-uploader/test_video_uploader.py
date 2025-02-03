import pytest
import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import hashlib
import os
import tempfile
from tqdm import tqdm
import time
import logging
import cProfile
import pstats
import sys
from pathlib import Path

# Add test directory to Python path
test_dir = str(Path(__file__).parent.parent.parent)
if test_dir not in sys.path:
    sys.path.append(test_dir)

from utils.port_forward import PortForwarder

API_URL = "http://localhost:8000"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(scope="session", autouse=True)
def port_forwarder():
    forwarder = PortForwarder()
    # Add all required services
    forwarder.start_port_forward("video-uploader", 8000, 8000)
    #forwarder.start_port_forward("database-service", 8011, 8011)
    #forwarder.start_port_forward("file-storage-service", 50051, 50051)
    #forwarder.start_port_forward("minio", 9000, 9000)
    
    yield forwarder
    
    forwarder.cleanup()

@pytest.fixture(scope="module")
def temp_dir():
    temp_dir = tempfile.TemporaryDirectory()
    yield temp_dir
    temp_dir.cleanup()

def _generate_large_file(filepath, size_in_gb):
    with open(filepath, 'wb') as f:
        for _ in range(size_in_gb * 1024):  # Write in 1MB chunks
            f.write(os.urandom(CHUNK_SIZE))

def _generate_small_file(filepath, size_in_mb):
    with open(filepath, 'wb') as f:
        for _ in range(size_in_mb):  # Write in 1MB chunks
            f.write(os.urandom(CHUNK_SIZE))

def create_callback(pbar):
    def callback(monitor):
        pbar.update(monitor.bytes_read - pbar.n)
    return callback

def _hash_file(filepath):
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(CHUNK_SIZE):
            md5.update(chunk)
            del chunk
    return md5.hexdigest()

def test_upload_download(temp_dir):
    logging.debug("\n=== Starting Video Upload/Download Test ===")
    
    video_path = os.path.join(temp_dir.name, 'test_video.mp4')
    downloaded_file = os.path.join(temp_dir.name, 'downloaded_video.mp4')
    _generate_large_file(video_path, 1)
    
    # Upload video
    logging.debug(f"\nUploading video from {video_path}...")
    total_size = os.path.getsize(video_path)
    
    with open(video_path, 'rb') as f:
        encoder = MultipartEncoder({
            'file': ('video.mp4', f, 'video/mp4')
        })
        
        with tqdm(total=total_size, desc="Uploading", unit='B', unit_scale=True) as pbar:
            monitor = MultipartEncoderMonitor(encoder, create_callback(pbar))
            
            response = requests.post(
                f"{API_URL}/upload/",
                data=monitor,
                headers={'Content-Type': monitor.content_type}
            )
    
    assert response.status_code == 200
    video_id = response.json()['id']
    logging.debug(f"Upload successful! Video ID: {video_id}")
    
    # Download video
    logging.debug(f"\nDownloading video with ID: {video_id}...")
    with requests.get(f"{API_URL}/video/{video_id}", stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get('content-length', 0))
        
        with tqdm(total=total_size, desc="Downloading", unit='B', unit_scale=True) as pbar:
            with open(downloaded_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
    
    # Compare files using generators
    logging.debug("\nComparing file hashes...")
    original_hash = _hash_file(video_path)
    downloaded_hash = _hash_file(downloaded_file)
    
    assert original_hash == downloaded_hash
    logging.debug("File comparison successful - hashes match!")

def test_delete_video(temp_dir):
    logging.debug("=== Starting Delete Video Test ===")
    
    # Generate a small file for testing
    small_video_path = os.path.join(temp_dir.name, 'small_test_video.mp4')
    _generate_small_file(small_video_path, size_in_mb=1)
    
    # Upload the small video for testing
    start_time = time.time()
    with open(small_video_path, 'rb') as f:
        encoder = MultipartEncoder({
            'file': ('small_test_video.mp4', f, 'video/mp4')
        })
        response = requests.post(
            f"{API_URL}/upload/",
            data=encoder,
            headers={'Content-Type': encoder.content_type}
        )
    upload_time = time.time() - start_time
    logging.debug(f"Upload time: {upload_time:.2f} seconds")
    
    assert response.status_code == 200
    video_id = response.json()['id']
    
    # Test successful deletion
    start_time = time.time()
    response = requests.delete(f"{API_URL}/video/{video_id}")
    delete_time = time.time() - start_time
    logging.debug(f"Delete time: {delete_time:.2f} seconds")
    
    assert response.status_code == 200
    assert response.json()['message'] == "Video deleted successfully"
    logging.debug("Delete video test passed")