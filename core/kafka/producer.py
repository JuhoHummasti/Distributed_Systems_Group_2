from confluent_kafka import Producer
import json

# Kafka configuration
conf = {
    'bootstrap.servers': 'localhost:29092,localhost:39092,localhost:49092',  # Update with your Kafka broker address
    'client.id': 'python-producer',
}

# Create a Producer instance
producer = Producer(conf)


def delivery_report(err, msg):
    """Callback for delivery reports from Kafka."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")


# Send messages to Kafka
topic = 'test-topic'  # Replace with your Kafka topic name

try:
    print("Enter messages to send to Kafka (Ctrl+C to exit):")
    while True:
        url = input("Enter URL: ")
        status = input("Enter status: ")
        video_title = input("Enter video title: ")
        message = json.dumps({
            "url": url,
            "status": status,
            "videoTitle": video_title
        })
        producer.produce(topic, value=message, callback=delivery_report)
        producer.flush()  # Ensure messages are delivered
except KeyboardInterrupt:
    print("\nExiting producer.")
except Exception as e:
    print(f"Error: {e}")
finally:
    producer.flush()