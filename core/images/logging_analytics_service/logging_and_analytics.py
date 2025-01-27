from confluent_kafka import Consumer, Producer, KafkaException, KafkaError
import json
import requests

# Kafka configuration
KAFKA_BROKER = 'localhost:29092,localhost:39092,localhost:49092'
CACHE_REQUEST_TOPIC = 'cache_request_topic'
CACHE_TOPIC = 'cache-topic'

# MongoDB FastAPI endpoint
MONGODB_API_URL = 'http://localhost:8000/api/v1/items/'

# Initialize Kafka consumer and producer
consumer_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'logging-analytics-group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe([CACHE_REQUEST_TOPIC])

producer_conf = {
    'bootstrap.servers': 'localhost:29092'
}
producer = Producer(producer_conf)

def send_to_cache_controller(video_data):
    print(f"Sending video data to cache controller: {video_data}")
    producer.produce(CACHE_TOPIC, json.dumps(video_data).encode('utf-8'))
    producer.flush()

def save_to_mongodb(video_data):
    # Get all items from the database
    response = requests.get(MONGODB_API_URL)
    if response.status_code != 200:
        print(f"Failed to retrieve data from MongoDB: {response.text}")
        return
    
    print(f"Retrieved data from MongoDB: {response.json()}")

    items = response.json()
    existing_item = next((item for item in items if item["videoTitle"] == video_data["video_id"]), None)
    try:

        print(f"Updating existing item: {existing_item}")
        # Update an existin item to status
        item_id = existing_item["_id"]
        print(f"Updating item with ID: {item_id}")
        update_url = f"{MONGODB_API_URL}{item_id}"

        if (video_data["event"] == "delete"):
            data = {
            "status": "in storage",
        }
        else:
            data = {
                "status": "cached"
            }

        update_response = requests.put(update_url, json=data)
        if update_response.status_code != 200:
            print(f"Failed to update data in MongoDB: {update_response.text}")
    except Exception as e:
        print(f"Error updating item, it probably doesn't exist: {e}")

def process_message(message):
    video_data = json.loads(message.value().decode('utf-8'))
    send_to_cache_controller(video_data)
    save_to_mongodb(video_data)

def main():
    try:
        print("Listening for messages. Press Ctrl+C to exit.")
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"End of partition reached {msg.topic()} [{msg.partition()}]")
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                process_message(msg)
    except KeyboardInterrupt:
        print("\nExiting consumer.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        consumer.close()

if __name__ == "__main__":
    main()
