import sys
import json
import grpc
import requests
import io
import os
from minio import Minio
from minio.error import S3Error
from confluent_kafka import Consumer, KafkaException, KafkaError

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '../file-storage-service'))
sys.path.insert(0, parent_dir)

import file_storage_service_pb2
import file_storage_service_pb2_grpc

class CacheController:
    def __init__(self):
        self.minio_client = Minio(
            "localhost:9000",
            access_key="myaccesskey",
            secret_key="mysecretkey",
            secure=False
        )
        self.bucket_name = "cache"
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = file_storage_service_pb2_grpc.FileStorageServiceStub(self.channel)
    
        self.consumer = Consumer({
                'bootstrap.servers': 'localhost:29092,localhost:39092,localhost:49092',
                'group.id': 'cache_controller_group',
                'auto.offset.reset': 'earliest'
            })
        self.consumer.subscribe(['cache-topic'])

    def cache_video(self, video_id):
        request = file_storage_service_pb2.VideoDownloadUrlRequest(video_id=video_id)
        response = self.stub.GetVideoDownloadUrl(request)
        print(response)
        if response.download_url:
            video_data = requests.get(response.download_url).content
            video_data_stream = io.BytesIO(video_data)
            self.minio_client.put_object(
                self.bucket_name,
                video_id,
                data=video_data_stream,
                length=len(video_data)
            )
            print(f"Video {video_id} cached successfully.")
        else:
            print(f"Failed to cache video {video_id}.")

    def list_cache(self):
        objects = self.minio_client.list_objects(self.bucket_name)
        for obj in objects:
            print(f"Object: {obj.object_name}, Size: {obj.size} bytes")

    def delete_video(self, video_id):
        try:
            self.minio_client.remove_object(self.bucket_name, video_id)
            print(f"Video {video_id} deleted successfully.")
        except S3Error as e:
            print(f"Failed to delete video {video_id}: {e}")

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
                        raise KafkaException(msg.error())
                
                message = json.loads(msg.value().decode('utf-8'))
                event = message.get("event")
                video_id = message.get("video_id")

                if event == "cache":
                    print(f"Received cache event for video ID: {video_id}")
                    self.cache_video(video_id)
                elif event == "delete":
                    print(f"Received delete event for video ID: {video_id}")
                    self.delete_video(video_id)
                else:
                    print(f"Unknown event type: {event}")
        except KeyboardInterrupt:
            print("\nExiting consumer.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.consumer.close()

if __name__ == '__main__':
    cache_controller = CacheController()
    #cache_controller.cache_video("karaandnate3.mp4")
    cache_controller.consume_kafka_messages()
