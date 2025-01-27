from confluent_kafka import Producer
import json

# Kafka configuration
KAFKA_BROKER = 'localhost:29092,localhost:39092,localhost:49092'
CACHE_REQUEST_TOPIC = 'cache_request_topic'

# Initialize Kafka producer
producer_conf = {
    'bootstrap.servers': KAFKA_BROKER
}
producer = Producer(producer_conf)

#    url: HttpUrl
#    status: str
#    videoTitle: str
#    time_created: datetime = datetime.utcnow()
#    time_updated: Optional[datetime] = None


def send_test_message():
    test_message = {
        "event": "cache",
        "video_id": "cboys.mp4",
    }
    producer.produce(CACHE_REQUEST_TOPIC, json.dumps(test_message).encode('utf-8'))
    producer.flush()
    print("Test message sent to cache_request_topic")

if __name__ == "__main__":
    send_test_message()
