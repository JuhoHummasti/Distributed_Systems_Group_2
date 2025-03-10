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
import requests
import json
import redis

# Configure logging
log_filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '_VideoStreamingRedisTest.log'
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

logger.info("Starting the tests with Redis analytics")

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Fetch video IDs from the API
def fetch_video_ids():
    try:
        url = "http://195.148.22.181:30080/api/videos"
        response = requests.get(url)
        if not response.ok:
            logger.error(f"Failed to fetch videos: {response.status_code}")
            return []
        
        videos = response.json()
        video_ids = [video["video_id"] for video in videos if video.get("status") != "processing"]
        
        if not video_ids:
            logger.warning("No valid video IDs found, using fallback IDs")
            return []
        
        logger.info(f"Fetched {len(video_ids)} video IDs")
        return video_ids
    except Exception as e:
        logger.error(f"Error fetching video IDs: {str(e)}")
        return []

# Get the video IDs at startup
VIDEO_IDS = fetch_video_ids()
logger.info(f"Using video IDs: {VIDEO_IDS}")

class VideoStreamingUser(HttpUser):
    host = "http://localhost"
    wait_time = between(0.5, 2)  # More aggressive timing

    @task
    def stream_video(self):
        # Simplified request pattern that doesn't adapt to network conditions
        video_id = random.choice(VIDEO_IDS)
        
        # Request playlist
        playlist_url = f"/stream/stream/{video_id}/playlist.m3u8"
        with self.client.get(playlist_url, timeout=3, catch_response=True, name="Get Playlist") as response:
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
            self.client.get(segment_url, timeout=2, name=f"Get Segment {segment}")  # Short timeout to trigger failures faster
            gevent.sleep(0.2)  # Very minimal delay between requests

def analyze_redis_cache_metrics():
    """Analyze Redis data to get cache hit/miss metrics"""
    try:
        # Get all keys from Redis
        all_keys = redis_client.keys("*")
        
        # Separate hit and miss keys
        hit_keys = [key for key in all_keys if key.startswith("hit:")]
        miss_keys = [key for key in all_keys if key.startswith("missed:")]
        
        # Collect hit data
        hit_counts = {}
        for key in hit_keys:
            try:
                data = json.loads(redis_client.get(key))
                file_path = key[4:]  # Remove 'hit:' prefix
                hit_counts[file_path] = data["count"]
            except Exception as e:
                logger.error(f"Error processing hit key {key}: {e}")
        
        # Collect miss data
        miss_counts = {}
        for key in miss_keys:
            try:
                data = json.loads(redis_client.get(key))
                file_path = key[7:]  # Remove 'missed:' prefix
                miss_counts[file_path] = data["count"]
            except Exception as e:
                logger.error(f"Error processing miss key {key}: {e}")
        
        # Calculate aggregate statistics
        total_hits = sum(hit_counts.values())
        total_misses = sum(miss_counts.values())
        total_requests = total_hits + total_misses
        hit_ratio = total_hits / total_requests if total_requests > 0 else 0
        
        # Create file-specific stats
        file_stats = {}
        
        # Combine hits and misses for each file
        all_files = set(list(hit_counts.keys()) + list(miss_counts.keys()))
        
        for file_path in all_files:
            hits = hit_counts.get(file_path, 0)
            misses = miss_counts.get(file_path, 0)
            total = hits + misses
            ratio = hits / total if total > 0 else 0
            
            # Parse video_id and file_name from the path
            # Path format is typically "{video_id}/{file_name}"
            if "/" in file_path:
                video_id, file_name = file_path.split("/", 1)
            else:
                video_id = "unknown"
                file_name = file_path
                
            file_stats[file_path] = {
                "video_id": video_id,
                "file_name": file_name,
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_ratio": ratio
            }
        
        return {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_requests": total_requests,
            "hit_ratio": hit_ratio,
            "file_stats": file_stats,
            "unique_files_accessed": len(all_files),
            "hit_keys_count": len(hit_keys),
            "miss_keys_count": len(miss_keys)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing Redis cache metrics: {e}")
        return {
            "error": str(e),
            "total_hits": 0,
            "total_misses": 0,
            "total_requests": 0,
            "hit_ratio": 0,
            "file_stats": {},
            "unique_files_accessed": 0,
            "hit_keys_count": 0,
            "miss_keys_count": 0
        }

@pytest.fixture
def locust_env():
    # Create a new environment for each test to avoid runner conflicts
    env = Environment(user_classes=[VideoStreamingUser], host="http://localhost")
    
    # Add connection error tracking
    env.connection_errors = 0
    
    @events.request.add_listener
    def on_request(request_type, name, response_time, response_length, response, 
                   context, exception, start_time, url, **kwargs):
        if exception:
            env.connection_errors += 1
    
    # Create the runner just before yielding
    env.create_local_runner()
    
    yield env
    
    # Properly cleanup the runner
    try:
        env.runner.quit()
    except Exception as e:
        logger.error(f"Error cleaning up runner: {e}")

def test_video_streaming_with_redis_analytics(locust_env):
    """Test video streaming performance and analyze cache behavior through Redis"""
    users = 10
    duration = 60  # 1 minute of test
    spawn_rate = 5
    
    # Start the Redis metrics collection
    def collect_redis_metrics():
        while True:
            try:
                metrics = analyze_redis_cache_metrics()
                logger.info("\n=== REDIS CACHE METRICS ===")
                logger.info(f"Total Hits: {metrics['total_hits']}")
                logger.info(f"Total Misses: {metrics['total_misses']}")
                logger.info(f"Total Requests: {metrics['total_requests']}")
                logger.info(f"Hit Ratio: {metrics['hit_ratio']:.2%}")
                logger.info(f"Unique Files Accessed: {metrics['unique_files_accessed']}")
                logger.info("=========================\n")
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
            gevent.sleep(10)  # Update every 10 seconds
    
    # Start metrics collection in background
    metrics_greenlet = gevent.spawn(collect_redis_metrics)
    
    # Start stats printer and history
    printer_greenlet = gevent.spawn(stats_printer(locust_env.stats))
    history_greenlet = gevent.spawn(stats_history, locust_env.runner)
    
    logger.info(f"Starting test with {users} users...")
    
    # Start the test
    locust_env.runner.start(users, spawn_rate=spawn_rate)
    
    # Wait for users to spawn
    time.sleep(users / spawn_rate + 1)  # Adding 1 second buffer
    
    # Record starting stats
    start_requests = locust_env.stats.total.num_requests
    start_failures = locust_env.stats.total.num_failures
    start_conn_errors = locust_env.connection_errors
    
    logger.info(f"All users spawned, running test for {duration} seconds...")
    
    # Run for the duration
    time.sleep(duration)
    
    # Final Redis metrics
    try:
        final_metrics = analyze_redis_cache_metrics()
    except Exception as e:
        logger.error(f"Error getting final metrics: {e}")
        final_metrics = {
            "total_hits": 0, 
            "total_misses": 0, 
            "total_requests": 0, 
            "hit_ratio": 0,
            "unique_files_accessed": 0
        }
    
    # Calculate metrics for this test
    total_requests = locust_env.stats.total.num_requests - start_requests
    total_failures = locust_env.stats.total.num_failures - start_failures
    total_conn_errors = locust_env.connection_errors - start_conn_errors
    
    if total_requests > 0:
        failure_rate = ((total_failures + total_conn_errors) / total_requests) * 100
    else:
        failure_rate = 0
        
    logger.info("\n=== FINAL TEST RESULTS ===")
    logger.info(f"Users: {users}")
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"RPS: {total_requests / duration:.1f}")
    logger.info(f"Failure Rate: {failure_rate:.2f}%")
    logger.info(f"Connection Errors: {total_conn_errors}")
    logger.info(f"HTTP Failures: {total_failures}")
    
    logger.info("\n=== FINAL REDIS CACHE METRICS ===")
    logger.info(f"Total Hits: {final_metrics['total_hits']}")
    logger.info(f"Total Misses: {final_metrics['total_misses']}")
    logger.info(f"Total Cache Requests: {final_metrics['total_requests']}")
    logger.info(f"Cache Hit Ratio: {final_metrics['hit_ratio']:.2%}")
    logger.info(f"Unique Files Accessed: {final_metrics['unique_files_accessed']}")
    
    # Top 5 most accessed files with their hit ratios
    if final_metrics.get('file_stats'):
        sorted_files = sorted(
            final_metrics['file_stats'].items(), 
            key=lambda x: x[1]['total'], 
            reverse=True
        )[:5]
        
        logger.info("\n=== TOP 5 MOST ACCESSED FILES ===")
        for file_path, stats in sorted_files:
            logger.info(f"File: {file_path}")
            logger.info(f"  Total Requests: {stats['total']}")
            logger.info(f"  Hit Ratio: {stats['hit_ratio']:.2%}")
            logger.info(f"  Hits: {stats['hits']}, Misses: {stats['misses']}")
    
    # Stop the metrics collection and the test
    metrics_greenlet.kill()
    printer_greenlet.kill()
    history_greenlet.kill()
    
    # Stop the test (redundant but good practice)
    locust_env.runner.stop()
    
    # Assertions for test validation
    assert total_requests > 0, "No requests were made during the test"

def test_aggressive_saturation_point_with_redis(locust_env):
    """Test that identifies the saturation point with Redis metrics"""
    users = 10  # Start with fewer users
    max_users = 500
    duration = 60  # Shorter test duration
    spawn_rate = 20  # Faster user spawn rate
    previous_rps = 0
    
    # Start stats printer and history
    printer_greenlet = gevent.spawn(stats_printer(locust_env.stats))
    history_greenlet = gevent.spawn(stats_history, locust_env.runner)
    
    # Start the Redis metrics collection
    def collect_redis_metrics():
        while True:
            try:
                metrics = analyze_redis_cache_metrics()
                logger.info("\n=== REDIS CACHE METRICS ===")
                logger.info(f"Total Hits: {metrics['total_hits']}")
                logger.info(f"Total Misses: {metrics['total_misses']}")
                logger.info(f"Total Requests: {metrics['total_requests']}")
                logger.info(f"Hit Ratio: {metrics['hit_ratio']:.2%}")
                logger.info("=========================\n")
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
            gevent.sleep(15)  # Update less frequently during saturation testing
    
    # Start metrics collection in background
    metrics_greenlet = gevent.spawn(collect_redis_metrics)
    
    saturation_metrics = None
    
    while users <= max_users:
        logger.info(f"=== Testing with {users} users ===")
        
        # Start the users
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
        
        # Get Redis metrics for this batch
        try:
            batch_redis_metrics = analyze_redis_cache_metrics()
            logger.info(f"Cache Hit Ratio: {batch_redis_metrics['hit_ratio']:.2%}")
            logger.info(f"Cache Hits: {batch_redis_metrics['total_hits']}, Misses: {batch_redis_metrics['total_misses']}")
        except Exception as e:
            logger.error(f"Error getting batch metrics: {e}")
            batch_redis_metrics = {"hit_ratio": 0, "total_hits": 0, "total_misses": 0}
        
        # Check for saturation indicators
        if batch_failure_rate > 5.0 or (users > 20 and current_rps < previous_rps * 0.7):
            logger.info(f"🔥 SATURATION DETECTED at {users} users!")
            logger.info(f"Failure rate: {batch_failure_rate:.2f}%, RPS: {current_rps:.1f}")
            saturation_metrics = batch_redis_metrics
            break
            
        # Save for comparison
        previous_rps = current_rps
        
        # Stop current users before starting more
        locust_env.runner.stop()
        time.sleep(3)  # Short break between test runs
            
        # Double the users for exponential growth
        users = users * 2
    
    # Final Redis metrics
    try:
        final_redis_metrics = analyze_redis_cache_metrics()
    except Exception as e:
        logger.error(f"Error getting final metrics: {e}")
        final_redis_metrics = {
            "total_hits": 0, 
            "total_misses": 0, 
            "total_requests": 0, 
            "hit_ratio": 0,
            "unique_files_accessed": 0
        }
    
    # Final stats
    logger.info("=== TEST COMPLETE ===")
    logger.info(f"Maximum sustainable users: {users // 2}")  # Last stable point
    logger.info(f"Total requests: {locust_env.stats.total.num_requests}")
    logger.info(f"Total failures: {locust_env.stats.total.num_failures}")
    logger.info(f"Connection errors: {locust_env.connection_errors}")
    
    logger.info("\n=== FINAL REDIS CACHE METRICS ===")
    logger.info(f"Total Hits: {final_redis_metrics['total_hits']}")
    logger.info(f"Total Misses: {final_redis_metrics['total_misses']}")
    logger.info(f"Total Cache Requests: {final_redis_metrics['total_requests']}")
    logger.info(f"Cache Hit Ratio: {final_redis_metrics['hit_ratio']:.2%}")
    
    # If we detected saturation, compare the cache metrics at saturation vs final
    if saturation_metrics:
        logger.info("\n=== CACHE METRICS AT SATURATION POINT ===")
        logger.info(f"Hit Ratio: {saturation_metrics['hit_ratio']:.2%}")
        logger.info(f"Cache Hits: {saturation_metrics['total_hits']}")
        logger.info(f"Cache Misses: {saturation_metrics['total_misses']}")
        
        # Calculate how the hit ratio changed after saturation
        if final_redis_metrics['hit_ratio'] > 0 and saturation_metrics['hit_ratio'] > 0:
            ratio_change = (final_redis_metrics['hit_ratio'] / saturation_metrics['hit_ratio'] - 1) * 100
            logger.info(f"Hit Ratio Change After Saturation: {ratio_change:.1f}%")
    
    # Stop the metrics collection and the test
    metrics_greenlet.kill()
    printer_greenlet.kill()
    history_greenlet.kill()
    
    # Stop the test
    locust_env.runner.stop()

if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])