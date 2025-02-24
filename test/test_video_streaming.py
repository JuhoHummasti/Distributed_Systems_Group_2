import pytest
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent
import random
import logging
import os
from datetime import datetime


VIDEO_IDS = [
    "48c7bb7c-75b2-4d4a-8178-f9a41069c6c7",
    "31c57765-5628-4777-ae15-060e935e56d8",
    "1a9b2095-f98c-451d-b68b-a7a42fef43f7"
]

# Configure logging
log_filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '_TestLocustVideoStreaming.log'
log_filepath = os.path.join(os.path.dirname(__file__), log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Starting the tests")

class VideoStreamingUser(HttpUser):
    host = "http://localhost"  # Base host URL
    wait_time = between(1, 5)  # Wait between 1 and 5 seconds between tasks

    @task
    def stream_video(self):
        
        # Randomly select a video ID to stream
        video_id = random.choice(VIDEO_IDS)
        
        # Get the HLS playlist
        playlist_url = f"/stream/stream/{video_id}/playlist.m3u8"
        response = self.client.get(playlist_url, timeout=5)  # Set timeout for the request
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        if response.status_code == 200:
            # Parse the playlist content to get segment URLs
            playlist_content = response.text
            segments = []
            for line in playlist_content.split('\n'):
                if line.endswith('.ts'):
                    segments.append(line.strip())

            # Request first 10 segments found in the playlist
            for segment in segments[:10]:
                segment_url = f"/stream/stream/{video_id}/{segment}"
                self.client.get(segment_url, timeout=3)  # Set timeout for the request
                gevent.sleep(0.5)  # Add small delay between segment requests
        else:
            logger.error(f"Failed to get the playlist for video ID: {video_id}")
            raise RuntimeError("Failed to get the playlist")
        
class VideoStreamingSimulatingUser(HttpUser):
    host = "http://localhost"  # Base host URL
    wait_time = between(1, 5)  # Wait between 1 and 5 seconds between tasks

    @task
    def stream_video(self):
        
        # Randomly select a video ID to stream
        video_id = random.choice(VIDEO_IDS)
        
        # Get the HLS playlist
        playlist_url = f"/stream/stream/{video_id}/playlist.m3u8"
        response = self.client.get(playlist_url, timeout=5)  # Set timeout for the request
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        if response.status_code == 200:
            # Parse the playlist content to get segment URLs
            playlist_content = response.text
            segments = []
            for line in playlist_content.split('\n'):
                if line.endswith('.ts'):
                    segments.append(line.strip())

            # Initialize buffer status (in seconds)
            buffer_time = 0
            segment_duration = 6  # Each segment is 6 seconds

            # Request first 10 segments found in the playlist
            for i, segment in enumerate(segments[:10]):
                segment_url = f"/stream/stream/{video_id}/{segment}"
                
                # Calculate remaining buffer time
                if buffer_time > 0:
                    buffer_time -= 0.5  # Account for the previous sleep
                
                # Adjust timeout based on buffer status
                if buffer_time < segment_duration:
                    # If buffer is low, use shorter timeout to get segment quickly
                    timeout = min(3, segment_duration - buffer_time)
                else:
                    # If buffer is healthy, can use longer timeout
                    timeout = 5
                
                self.client.get(segment_url, timeout=timeout)
                buffer_time += segment_duration  # Add new segment to buffer
                
                # Sleep less if buffer is low, more if buffer is healthy
                sleep_time = min(0.5, buffer_time / 2) if buffer_time < segment_duration * 2 else 0.5
                gevent.sleep(sleep_time)
        else:
            logger.error(f"Failed to get the playlist for video ID: {video_id}")
            raise RuntimeError("Failed to get the playlist")
        

@pytest.fixture(scope="module")
def locust_env():
    # Set up Locust environment
    env = Environment(user_classes=[VideoStreamingSimulatingUser])

    # Log the number of users and requests
    @events.request.add_listener
    def log_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
        if exception:
            logger.error(f"Request: {request_type} {name} - Exception: {exception}")
        else:
            logger.info(f"Request: {request_type} {name} - Response time: {response_time} ms - Response length: {response_length} bytes")

    @events.spawning_complete.add_listener
    def log_user_count(user_count):
        logger.info(f"Number of users: {user_count}")

    yield env
    
    # Stop the test
    env.runner.quit()
    
def test_video_streaming_20_users(locust_env):
    _test_video_streaming_users(locust_env, users=20, duration=60, spawn_rate=2)
    
def test_video_streaming_until_failure(locust_env):
    """Test increasing concurrent users until failure rate exceeds 2%"""
    initial_users = 30
    step = 10
    max_users = 500
    duration = 60
    spawn_rate = 10
    failure_rate_limit = 2.0
    
    current_users = initial_users
    while current_users <= max_users:
        logger.info(f"Testing with {current_users} concurrent users")
        _test_video_streaming_users(locust_env, users=current_users, duration=duration, spawn_rate=spawn_rate)
        
        # Get failure stats
        failure_count = locust_env.stats.total.num_failures
        total_requests = locust_env.stats.total.num_requests
        
        failure_rate = (failure_count / total_requests * 100) if total_requests > 0 else 0
        
        logger.info(f"Failure rate: {failure_rate:.2f}%")
        
        if failure_rate > failure_rate_limit:
            logger.info(f"Failure threshold exceeded at {current_users} users")
            break
            
        current_users += step
    
def _test_video_streaming_users(locust_env, users=50, duration=60, spawn_rate=5):
    logger.info(f"Starting the test with {users} users and {duration} seconds duration")
        
    # Full cleanup of previous run
    if hasattr(locust_env, 'runner') and locust_env.runner:
        locust_env.runner.quit()
        locust_env.runner = None
        
    # Reset stats before next iteration
    locust_env.stats.reset_all()
    locust_env.stats.clear_all()

    # Create fresh runner
    locust_env.create_local_runner()

    # Start new stats collection
    gevent.spawn(stats_printer(locust_env.stats))
    gevent.spawn(stats_history, locust_env.runner)

    # Start the test
    locust_env.runner.start(users, spawn_rate=spawn_rate)
    # Run the test for a specific duration
    gevent.spawn_later(duration, lambda: locust_env.runner.quit())
    locust_env.runner.greenlet.join()

if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])