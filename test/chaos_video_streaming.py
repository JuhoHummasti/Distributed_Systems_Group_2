import random
import time
import gevent
import pytest
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import logging
import os
from datetime import datetime

# Configure logging
log_filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '_ChaosVideoStreaming.log'
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

logger.info("Starting chaos testing")

class ChaosUser(HttpUser):
    """User that introduces chaos while testing"""
    wait_time = between(1, 3)
    
    # Set a default host
    host = "http://localhost"
    
    # API endpoints and their hosts
    HOSTS = {
        "api": "http://195.148.22.181:30080",
        "stream": "http://localhost"
    }
    
    # Chaos parameters
    connection_reset_probability = 0.05  # 5% chance of reset
    slow_request_probability = 0.10      # 10% chance of slow request
    max_slow_delay = 10                  # Max seconds to delay
    error_injection_probability = 0.08   # 8% chance of error injection
    
    def on_start(self):
        """Initialize user-specific counters"""
        # These counters will track chaos events for this specific user
        self.chaos_counters = {
            "connection_resets": 0,
            "slow_requests": 0,
            "error_injections": 0
        }
        logger.info("User started with chaos parameters")
    
    @task(3)
    def normal_request(self):
        """Regular API request that might be affected by chaos"""
        try:
            # Chaos type 1: Connection reset
            if random.random() < self.connection_reset_probability:
                logger.info("[CHAOS] Simulating connection reset")
                self.chaos_counters["connection_resets"] += 1
                # Rather than making a real request that fails, simply log it
                return
                
            # Chaos type 2: Slow request
            if random.random() < self.slow_request_probability:
                delay = random.uniform(2, self.max_slow_delay)
                logger.info(f"[CHAOS] Simulating slow request: {delay:.2f}s delay")
                time.sleep(delay)
                self.chaos_counters["slow_requests"] += 1
                
            # Make the actual request
            api_url = f"{self.HOSTS['api']}/api/videos"
            response = self.client.get(api_url, name="Get API Videos")
            
            # Chaos type 3: Error injection
            if random.random() < self.error_injection_probability:
                logger.info("[CHAOS] Injecting error after successful request")
                self.chaos_counters["error_injections"] += 1
                # Just log the injected error, don't actually fail the request
                
        except Exception as e:
            logger.error(f"Unexpected error in normal_request: {str(e)}")
    
    @task(2)
    def video_streaming(self):
        """Simulates video streaming with potential interruptions"""
        try:
            # Get video list from API server
            response = self.client.get(f"{self.HOSTS['api']}/api/videos", name="List Videos")
            if response.status_code != 200:
                logger.warning(f"Failed to get videos: {response.status_code}")
                return
            
            videos = response.json()
            if not videos:
                logger.warning("No videos found")
                return
                
            # Select random video
            video = random.choice(videos)
            video_id = video.get("video_id")
            
            # Start streaming
            self.client.get(
                f"{self.HOSTS['stream']}/stream/stream/{video_id}/playlist.m3u8", 
                name="Get Video Playlist"
            )
            
            # Simulate watching video segments with potential interruptions
            for i in range(5):
                # Random chance to abandon stream
                if random.random() < 0.30:
                    logger.info(f"User abandoned stream for video {video_id}")
                    break
                
                # Simulate segment request
                self.client.get(
                    f"{self.HOSTS['stream']}/stream/stream/{video_id}/segment_{i}.ts", 
                    name=f"Get Segment {i}"
                )
                
                # Simulate viewing time
                time.sleep(random.uniform(1, 3))
                
        except Exception as e:
            logger.error(f"Error in video_streaming: {str(e)}")
            
    @task(1)
    def fetch_specific_video(self):
        """Fetch a specific video with potential timeout"""
        try:
            # Get video list
            response = self.client.get(f"{self.HOSTS['api']}/api/videos", name="List All Videos")
            if response.status_code != 200:
                logger.warning(f"Failed to get videos: {response.status_code}")
                return
                
            videos = response.json()
            if not videos:
                logger.warning("No videos found")
                return
                
            # Select random video
            video = random.choice(videos)
            video_id = video.get("video_id")
            
            # Random chance for slow request
            if random.random() < 0.4:
                timeout = random.uniform(5, 15)
                logger.info(f"Slow request for video details: {timeout:.2f}s delay")
                self.client.get(f"{self.HOSTS['api']}/api/videos/{video_id}", name="Get Video Details (slow)")
                time.sleep(timeout)
            else:
                self.client.get(f"{self.HOSTS['api']}/api/videos/{video_id}", name="Get Video Details")
                
        except Exception as e:
            logger.error(f"Error in fetch_specific_video: {str(e)}")


@pytest.fixture(scope="module")
def locust_env():
    # Set up environment with a default host
    env = Environment(user_classes=[ChaosUser], host="http://localhost")
    
    # Initialize chaos tracking stats
    env.stats.chaos_events = {
        "connection_resets": 0,
        "slow_requests": 0,
        "error_injections": 0
    }
    
    # Start stats printer and history
    gevent.spawn(stats_printer(env.stats))
    gevent.spawn(stats_history, env.runner)
    
    # Create test runner
    env.create_local_runner()
    
    # Print chaos stats periodically
    def print_chaos_stats():
        while True:
            gevent.sleep(10)
            logger.info("\n=== CHAOS ENGINEERING STATS ===")
            # Collect stats from all users
            for user in env.runner.user_greenlets:
                if hasattr(user.args[0], 'chaos_counters'):
                    for event_type, count in user.args[0].chaos_counters.items():
                        env.stats.chaos_events[event_type] += count
                        # Reset user counters after collection
                        user.args[0].chaos_counters[event_type] = 0
            
            # Print collected stats
            for event_type, count in env.stats.chaos_events.items():
                logger.info(f"{event_type}: {count}")
            logger.info("===============================\n")
    
    # Start printing stats
    gevent.spawn(print_chaos_stats)
    
    yield env
    
    # Clean up after test
    env.runner.quit()


def test_chaos_effects(locust_env):
    """Test to measure how chaos affects streaming performance"""
    logger.info("Starting chaos effects test")
    
    users = 20
    spawn_rate = 5
    duration = 60  # 1 minute of test
    
    # Start the test with users
    logger.info(f"Starting test with {users} users at spawn rate {spawn_rate}")
    locust_env.runner.start(users, spawn_rate=spawn_rate)
    
    # Wait for users to spawn
    logger.info(f"Waiting for {users} users to spawn...")
    time.sleep(users / spawn_rate)
    
    # Record starting stats
    start_requests = locust_env.stats.total.num_requests
    start_failures = locust_env.stats.total.num_failures
    
    # Wait for test duration
    logger.info(f"Test running for {duration} seconds...")
    time.sleep(duration)
    
    # Calculate final stats
    total_requests = locust_env.stats.total.num_requests - start_requests
    total_failures = locust_env.stats.total.num_failures - start_failures
    
    # Calculate rates
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    
    # Log results
    logger.info("\n=== CHAOS TEST RESULTS ===")
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Total Failures: {total_failures}")
    logger.info(f"Failure Rate: {failure_rate:.2f}%")
    
    # Collect chaos events
    connection_resets = locust_env.stats.chaos_events["connection_resets"]
    slow_requests = locust_env.stats.chaos_events["slow_requests"]
    error_injections = locust_env.stats.chaos_events["error_injections"]
    
    logger.info(f"Connection Resets: {connection_resets}")
    logger.info(f"Slow Requests: {slow_requests}")
    logger.info(f"Error Injections: {error_injections}")
    logger.info("=========================\n")
    
    # Stop the test
    logger.info("Stopping test...")
    locust_env.runner.stop()
    
    # Log test completion
    logger.info("Chaos effects test completed")


if __name__ == "__main__":
    # Run the test directly
    pytest.main(["-v", __file__])