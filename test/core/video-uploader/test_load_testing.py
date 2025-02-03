import pytest
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent
import os
import tempfile
import random
from requests_toolbelt import MultipartEncoder
import sys
from pathlib import Path

# Add path for imports
test_dir = str(Path(__file__).parent.parent.parent)
if test_dir not in sys.path:
    sys.path.append(test_dir)

class VideoUser(HttpUser):
    host = "http://localhost:8000"  # Set default host
    wait_time = between(0.1, 0.5)  # Wait 0.1 - 0.5 seconds between tasks
    video_ids = []  # Store uploaded video IDs
    
    def on_start(self):
        """Setup before tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.small_video = self._generate_test_video(1)  # 1MB video
        self.medium_video = self._generate_test_video(5)  # 5MB video
        
    def on_stop(self):
        """Cleanup after tests"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            for file in [self.small_video, self.medium_video]:
                if os.path.exists(file):
                    os.remove(file)
            os.rmdir(self.temp_dir)

    def _generate_test_video(self, size_mb):
        """Generate a test video file of specified size in MB"""
        filepath = os.path.join(self.temp_dir, f'test_video_{size_mb}mb.mp4')
        with open(filepath, 'wb') as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
        return filepath

    @task(3)  # Higher weight for uploads
    def upload_video(self):
        """Test video upload with different file sizes"""
        video_path = random.choice([self.small_video, self.medium_video])
        
        with open(video_path, 'rb') as f:
            encoder = MultipartEncoder({
                'file': ('video.mp4', f, 'video/mp4')
            })
            
            response = self.client.post(
                "/upload/",
                data=encoder,
                headers={'Content-Type': encoder.content_type}
            )
            
            if response.status_code == 200:
                video_id = response.json()['id']
                self.video_ids.append(video_id)

    @task(2)
    def download_video(self):
        """Test video download"""
        if not self.video_ids:
            return
            
        video_id = random.choice(self.video_ids)
        with self.client.get(
            f"/video/{video_id}",
            stream=True,
            catch_response=True
        ) as response:
            try:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:  # Store chunk data to avoid unused variable warning
                        _ = chunk
                response.success()
            except Exception as e:
                response.failure(str(e))

    @task(1)
    def list_videos(self):
        """Test listing videos"""
        self.client.get("/videos/")

    @task(1)
    def delete_video(self):
        """Test video deletion"""
        if not self.video_ids:
            return
            
        video_id = random.choice(self.video_ids)
        response = self.client.delete(f"/video/{video_id}")
        
        if response.status_code == 200:
            self.video_ids.remove(video_id)

    @task(1)
    def check_video_status(self):
        """Test video status check"""
        if not self.video_ids:
            return
            
        video_id = random.choice(self.video_ids)
        self.client.get(f"/video/{video_id}/status")

@pytest.fixture(scope="module")
def load_test_env():
    # Set up the environment with host
    env = Environment(
        user_classes=[VideoUser],
        host="http://localhost:8000"  # Explicitly set host
    )
    env.create_local_runner()
    
    # Start the test
    try:
        env.runner.start(10, spawn_rate=1)
        
        # Start stats printer
        gevent.spawn(stats_printer(env.stats))
        
        # Start stats history
        gevent.spawn(stats_history, env.runner)
        
        yield env
    
    finally:
        # Cleanup
        env.runner.quit()

def test_load_performance(load_test_env):
    try:
        # Run for 60 seconds
        gevent.spawn_later(60, lambda: load_test_env.runner.quit())
        load_test_env.runner.greenlet.join(timeout=70)  # Add timeout
        
        # Get the stats
        stats = load_test_env.stats.total
        
        # Enhanced assertions with better error messages
        assert stats.avg_response_time < 2000, (
            f"Average response time {stats.avg_response_time}ms exceeds limit of 2000ms"
        )
        assert stats.fail_ratio < 0.1, (
            f"Failure rate {stats.fail_ratio*100}% exceeds limit of 10%"
        )
        
    except gevent.Timeout:
        pytest.fail("Load test timed out")
    except Exception as e:
        pytest.fail(f"Load test failed: {str(e)}")

def test_upload_stress(load_test_env):
    try:
        load_test_env.runner.start(20, spawn_rate=2)
        gevent.spawn_later(30, lambda: load_test_env.runner.quit())
        load_test_env.runner.greenlet.join(timeout=40)
        
        upload_stats = load_test_env.stats.get("/upload/", "POST")
        assert upload_stats.avg_response_time < 5000
        assert upload_stats.fail_ratio < 0.15
        
    except Exception as e:
        pytest.fail(f"Upload stress test failed: {str(e)}")

def test_download_concurrency(load_test_env):
    try:
        load_test_env.runner.start(15, spawn_rate=5)
        gevent.spawn_later(30, lambda: load_test_env.runner.quit())
        load_test_env.runner.greenlet.join(timeout=40)
        
        download_stats = load_test_env.stats.get("/video/*", "GET")
        assert download_stats.avg_response_time < 3000
        assert download_stats.fail_ratio < 0.1
        
    except Exception as e:
        pytest.fail(f"Download concurrency test failed: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__])