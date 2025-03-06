import pytest
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent
import random
import logging
import os
from datetime import datetime
import time


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
    host = "http://localhost"
    wait_time = between(0.5, 2)  # More aggressive timing

    @task
    def stream_video(self):
        # Simplified request pattern that doesn't adapt to network conditions
        video_id = random.choice(VIDEO_IDS)
        
        # Request playlist
        playlist_url = f"/stream/stream/{video_id}/playlist.m3u8"
        with self.client.get(playlist_url, timeout=3, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to get playlist: {response.status_code}")
                return
                
            segments = []
            for line in response.text.split('\n'):
                if line.endswith('.ts'):
                    segments.append(line.strip())
        
        # Request segments with fixed timeout
        for segment in segments[:5]:  # Reduced number for more concentrated load
            segment_url = f"/stream/stream/{video_id}/{segment}"
            self.client.get(segment_url, timeout=2)  # Short timeout to trigger failures faster
            gevent.sleep(0.2)  # Very minimal delay between requests

@pytest.fixture(scope="module")
def locust_env():
    # Setup similar to original
    env = Environment(user_classes=[VideoStreamingUser])
    
    # Add connection error tracking
    env.connection_errors = 0
    
    @events.request.add_listener
    def on_request(request_type, name, response_time, response_length, response, 
                   context, exception, start_time, url, **kwargs):
        if exception:
            env.connection_errors += 1
            
    yield env
    env.runner.quit()

def test_aggressive_saturation_point(locust_env):
    """Test that quickly identifies the saturation point with exponential user growth"""
    users = 10  # Start with fewer users
    max_users = 500
    duration = 60  # Shorter test duration
    spawn_rate = 20  # Faster user spawn rate
    total_failures = 0
    total_requests = 0
    
    # Don't reset the runner between iterations to maintain pressure
    locust_env.create_local_runner()
    gevent.spawn(stats_printer(locust_env.stats))
    gevent.spawn(stats_history, locust_env.runner)
    
    while users <= max_users:
        logger.info(f"=== Testing with {users} users ===")
        
        # Start the additional users (don't reset)
        locust_env.runner.start(users, spawn_rate=spawn_rate)
        
        # Wait for users to spawn
        spawn_time = max(users / spawn_rate, 1)
        time.sleep(spawn_time)
        
        # Record the starting stats
        start_requests = locust_env.stats.total.num_requests
        start_failures = locust_env.stats.total.num_failures
        start_conn_errors = locust_env.connection_errors
        
        # Run for the duration
        time.sleep(duration)
        
        # Calculate metrics for this batch of users
        new_requests = locust_env.stats.total.num_requests - start_requests
        new_failures = locust_env.stats.total.num_failures - start_failures
        new_conn_errors = locust_env.connection_errors - start_conn_errors
        
        if new_requests > 0:
            batch_failure_rate = ((new_failures + new_conn_errors) / new_requests) * 100
        else:
            batch_failure_rate = 0
            
        # Track current RPS
        current_rps = new_requests / duration
            
        logger.info(f"Users: {users}, RPS: {current_rps:.1f}, Failure Rate: {batch_failure_rate:.2f}%")
        logger.info(f"Connection Errors: {new_conn_errors}, HTTP Failures: {new_failures}")
        
        # Check for saturation indicators - either high failure rate or dramatic RPS drop
        if batch_failure_rate > 5.0 or (users > 20 and current_rps < previous_rps * 0.7):
            logger.info(f"🔥 SATURATION DETECTED at {users} users!")
            logger.info(f"Failure rate: {batch_failure_rate:.2f}%, RPS: {current_rps:.1f}")
            break
            
        # Save for comparison
        previous_rps = current_rps
            
        # Double the users for exponential growth
        users = users * 2
    
    # Final stats
    logger.info("=== TEST COMPLETE ===")
    logger.info(f"Maximum sustainable users: {users // 2}")  # Last stable point
    logger.info(f"Total requests: {locust_env.stats.total.num_requests}")
    logger.info(f"Total failures: {locust_env.stats.total.num_failures}")
    logger.info(f"Connection errors: {locust_env.connection_errors}")

@pytest.mark.skip(reason="Skipping aggressive saturation test")
def test_enhanced_saturation_point(locust_env):
    """Test that identifies a precise saturation point using exponential growth followed by binary search"""
    users = 10  # Start with fewer users
    max_users = 500
    duration = 60  # Test duration for each step
    spawn_rate = 20  # User spawn rate
    total_failures = 0
    total_requests = 0
    previous_rps = 0
    
    # Don't reset the runner between iterations
    locust_env.create_local_runner()
    gevent.spawn(stats_printer(locust_env.stats))
    gevent.spawn(stats_history, locust_env.runner)
    
    # Phase 1: Exponential growth to find approximate saturation point
    lower_bound = 10
    upper_bound = max_users
    saturation_detected = False
    
    while users <= max_users and not saturation_detected:
        logger.info(f"=== Testing with {users} users ===")
        
        # Start the additional users (don't reset)
        locust_env.runner.start(users, spawn_rate=spawn_rate)
        
        # Wait for users to spawn
        spawn_time = max(users / spawn_rate, 1)
        time.sleep(spawn_time)
        
        # Record the starting stats
        start_requests = locust_env.stats.total.num_requests
        start_failures = locust_env.stats.total.num_failures
        start_conn_errors = locust_env.connection_errors
        
        # Run for the duration
        time.sleep(duration)
        
        # Calculate metrics for this batch
        new_requests = locust_env.stats.total.num_requests - start_requests
        new_failures = locust_env.stats.total.num_failures - start_failures
        new_conn_errors = locust_env.connection_errors - start_conn_errors
        
        if new_requests > 0:
            batch_failure_rate = ((new_failures + new_conn_errors) / new_requests) * 100
        else:
            batch_failure_rate = 0
            
        current_rps = new_requests / duration
        logger.info(f"Users: {users}, RPS: {current_rps:.1f}, Failure Rate: {batch_failure_rate:.2f}%")
        
        # Check for saturation indicators
        if batch_failure_rate > 5.0 or (users > 20 and current_rps < previous_rps * 0.7):
            logger.info(f"🔥 SATURATION DETECTED at {users} users!")
            upper_bound = users
            lower_bound = users // 2  # Last stable point
            saturation_detected = True
        else:
            previous_rps = current_rps
            lower_bound = users
            users = users * 2  # Exponential growth
    
    # Phase 2: Binary search to find precise saturation point
    if saturation_detected:
        logger.info(f"=== Refining between {lower_bound} and {upper_bound} users ===")
        
        while upper_bound - lower_bound > 5:  # Precision threshold
            mid_point = (lower_bound + upper_bound) // 2
            users = mid_point
            
            logger.info(f"=== Testing with {users} users (refinement) ===")
            
            # Stop and restart at the midpoint
            locust_env.runner.stop()
            time.sleep(5)  # Allow system to stabilize
            locust_env.runner.start(users, spawn_rate=spawn_rate)
            
            # Wait for users to spawn
            spawn_time = max(users / spawn_rate, 1)
            time.sleep(spawn_time)
            
            # Record the starting stats
            start_requests = locust_env.stats.total.num_requests
            start_failures = locust_env.stats.total.num_failures
            start_conn_errors = locust_env.connection_errors
            
            # Run for the duration
            time.sleep(duration)
            
            # Calculate metrics
            new_requests = locust_env.stats.total.num_requests - start_requests
            new_failures = locust_env.stats.total.num_failures - start_failures
            new_conn_errors = locust_env.connection_errors - start_conn_errors
            
            if new_requests > 0:
                batch_failure_rate = ((new_failures + new_conn_errors) / new_requests) * 100
            else:
                batch_failure_rate = 0
                
            current_rps = new_requests / duration
            logger.info(f"Users: {users}, RPS: {current_rps:.1f}, Failure Rate: {batch_failure_rate:.2f}%")
            
            # Update bounds based on test results
            if batch_failure_rate > 5.0 or current_rps < previous_rps * 0.7:
                upper_bound = mid_point
            else:
                lower_bound = mid_point
                previous_rps = current_rps
    
    # Final stats
    logger.info("=== TEST COMPLETE ===")
    logger.info(f"Precise saturation point: ~{lower_bound} users")
    logger.info(f"Total requests: {locust_env.stats.total.num_requests}")
    logger.info(f"Total failures: {locust_env.stats.total.num_failures}")
    logger.info(f"Connection errors: {locust_env.connection_errors}")

if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])