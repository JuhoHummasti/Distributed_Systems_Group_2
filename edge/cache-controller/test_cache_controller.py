import unittest
from confluent_kafka import Producer
import time
import json
from app import CacheController

class TestCacheController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up Kafka producer
        kafka_conf = {
            'bootstrap.servers': 'localhost:29092',
            'client.id': 'cache_controller_group',
        }
        cls.producer = Producer(kafka_conf)
        cls.cache_controller = CacheController()

    def send_kafka_message(self, topic, message):
        self.producer.produce(topic, json.dumps(message).encode('utf-8'))
        self.producer.flush()

    def test_cache_video(self):
        # Simulate sending a cache request to the Kafka topic
        video_id = "karaandnate3.mp4"
        message = {
            "event": "cache",
            "video_id": video_id
        }

        self.send_kafka_message('cache-topic', message)

        # Allow some time for the consumer to process the message
        time.sleep(5)

        # Check if the video is cached
        objects = self.cache_controller.minio_client.list_objects(self.cache_controller.bucket_name)
        cached_videos = [obj.object_name for obj in objects]
        self.assertIn(video_id, cached_videos)


    def test_delete_video(self):
        # Simulate sending a delete request to the Kafka topic
        video_id = "karaandnate3.mp4"
        message = {
            "event": "delete",
            "video_id": video_id,
        }
        self.send_kafka_message('cache-topic', message)

        # Allow some time for the consumer to process the message
        time.sleep(5)

        # Check if the video is deleted
        objects = self.cache_controller.minio_client.list_objects(self.cache_controller.bucket_name)
        cached_videos = [obj.object_name for obj in objects]
        self.assertNotIn(video_id, cached_videos)

if __name__ == '__main__':
    unittest.main()