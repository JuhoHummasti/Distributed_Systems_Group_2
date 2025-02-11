import sys
import json
import grpc
import requests
import io
import os
from minio import Minio
from minio.error import S3Error
from confluent_kafka import Consumer, KafkaException, KafkaError
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time
from threading import Thread

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '../file-storage-service'))
sys.path.insert(0, parent_dir)

import file_storage_service_pb2
import file_storage_service_pb2_grpc

# Define Prometheus metrics
CACHE_OPERATIONS = Counter('cache_operations_total', 'Number of cache operations', ['operation', 'status'])
KAFKA_MESSAGES = Counter('kafka_messages_total', 'Number of Kafka messages processed', ['event_type', 'status'])
CACHE_SIZE = Gauge('cache_size_bytes', 'Total size of cached videos in bytes')
VIDEO_SIZE = Gauge('video_size_bytes', 'Size of individual videos in cache', ['video_id'])
CACHE_OPERATION_DURATION = Histogram('cache_operation_duration_seconds', 
                                   'Time spent on cache operations',
                                   ['operation'],
                                   buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0))
MINIO_CONNECTION_STATUS = Gauge('minio_connection_status', 'MinIO connection status (1 for connected, 0 for disconnected)')
KAFKA_CONNECTION_STATUS = Gauge('kafka_connection_status', 'Kafka connection status (1 for connected, 0 for disconnected)')
GRPC_CONNECTION_STATUS = Gauge('grpc_connection_status', 'gRPC connection status (1 for connected, 0 for disconnected)')

class CacheController:
    def __init__(self):
        # Start Prometheus HTTP server
        start_http_server(5001)
        
        try:
            self.minio_client = Minio(
                "minio:9000",
                access_key="myaccesskey",
                secret_key="mysecretkey",
                secure=False
            )
            self.bucket_name = "cache"
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
            MINIO_CONNECTION_STATUS.set(1)
        except Exception as e:
            print(f"MinIO connection error: {e}")
            MINIO_CONNECTION_STATUS.set(0)

        try:
            self.channel = grpc.insecure_channel('localhost:50051')
            self.stub = file_storage_service_pb2_grpc.FileStorageServiceStub(self.channel)
            GRPC_CONNECTION_STATUS.set(1)
        except Exception as e:
            print(f"gRPC connection error: {e}")
            GRPC_CONNECTION_STATUS.set(0)

        try:
            self.consumer = Consumer({
                'bootstrap.servers': 'localhost:29092,localhost:39092,localhost:49092',
                'group.id': 'cache_controller_group',
                'auto.offset.reset': 'earliest'
            })
            self.consumer.subscribe(['cache-topic'])
            KAFKA_CONNECTION_STATUS.set(1)
        except Exception as e:
            print(f"Kafka connection error: {e}")
            KAFKA_CONNECTION_STATUS.set(0)

        # Start cache size monitoring thread
        self.monitor_thread = Thread(target=self._monitor_cache_size, daemon=True)
        self.monitor_thread.start()

    def _monitor_cache_size(self):
        """Periodically update cache size metrics"""
        while True:
            try:
                total_size = 0
                objects = self.minio_client.list_objects(self.bucket_name)
                for obj in objects:
                    total_size += obj.size
                    VIDEO_SIZE.labels(video_id=obj.object_name).set(obj.size)
                CACHE_SIZE.set(total_size)
            except Exception as e:
                print(f"Error monitoring cache size: {e}")
            time.sleep(60)  # Update every minute

    def cache_video(self, video_id):
        start_time = time.time()
        try:
            request = file_storage_service_pb2.VideoDownloadUrlRequest(video_id=video_id)
            response = self.stub.GetVideoDownloadUrl(request)
            
            if response.download_url:
                video_data = requests.get(response.download_url).content
                video_data_stream = io.BytesIO(video_data)
                self.minio_client.put_object(
                    self.bucket_name,
                    video_id,
                    data=video_data_stream,
                    length=len(video_data)
                )
                VIDEO_SIZE.labels(video_id=video_id).set(len(video_data))
                CACHE_OPERATIONS.labels(operation='cache', status='success').inc()
                print(f"Video {video_id} cached successfully.")
            else:
                CACHE_OPERATIONS.labels(operation='cache', status='error').inc()
                print(f"Failed to cache video {video_id}.")
        except Exception as e:
            CACHE_OPERATIONS.labels(operation='cache', status='error').inc()
            print(f"Error caching video {video_id}: {e}")
        finally:
            CACHE_OPERATION_DURATION.labels(operation='cache').observe(time.time() - start_time)

    def list_cache(self):
        try:
            objects = self.minio_client.list_objects(self.bucket_name)
            for obj in objects:
                print(f"Object: {obj.object_name}, Size: {obj.size} bytes")
            CACHE_OPERATIONS.labels(operation='list', status='success').inc()
        except Exception as e:
            CACHE_OPERATIONS.labels(operation='list', status='error').inc()
            print(f"Error listing cache: {e}")

    def delete_video(self, video_id):
        start_time = time.time()
        try:
            self.minio_client.remove_object(self.bucket_name, video_id)
            VIDEO_SIZE.labels(video_id=video_id).set(0)
            CACHE_OPERATIONS.labels(operation='delete', status='success').inc()
            print(f"Video {video_id} deleted successfully.")
        except S3Error as e:
            CACHE_OPERATIONS.labels(operation='delete', status='error').inc()
            print(f"Failed to delete video {video_id}: {e}")
        finally:
            CACHE_OPERATION_DURATION.labels(operation='delete').observe(time.time() - start_time)

    def consume_kafka_messages(self):
        try:
            print("Listening for messages. Press Ctrl+C to exit.")
            while True:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(msg.error())
                        KAFKA_MESSAGES.labels(event_type='error', status='error').inc()
                        raise KafkaException(msg.error())
                
                message = json.loads(msg.value().decode('utf-8'))
                event = message.get("event")
                video_id = message.get("video_id")

                if event == "cache":
                    print(f"Received cache event for video ID: {video_id}")
                    KAFKA_MESSAGES.labels(event_type='cache', status='received').inc()
                    self.cache_video(video_id)
                elif event == "delete":
                    print(f"Received delete event for video ID: {video_id}")
                    KAFKA_MESSAGES.labels(event_type='delete', status='received').inc()
                    self.delete_video(video_id)
                else:
                    print(f"Unknown event type: {event}")
                    KAFKA_MESSAGES.labels(event_type='unknown', status='error').inc()

        except KeyboardInterrupt:
            print("\nExiting consumer.")
        except Exception as e:
            print(f"Error: {e}")
            KAFKA_MESSAGES.labels(event_type='error', status='error').inc()
        finally:
            self.consumer.close()
            KAFKA_CONNECTION_STATUS.set(0)

if __name__ == '__main__':
    cache_controller = CacheController()
    cache_controller.consume_kafka_messages()