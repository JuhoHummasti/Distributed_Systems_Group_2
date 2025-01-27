from confluent_kafka import Consumer, KafkaException, KafkaError
import requests
import json

# Kafka configuration
conf = {
    'bootstrap.servers': 'localhost:29092,localhost:39092,localhost:49092',  # Update with your Kafka broker address
    'group.id': 'python-consumer-group',
    'auto.offset.reset': 'earliest',  # Start reading from the earliest message
}

# Create a Consumer instance
consumer = Consumer(conf)

# Subscribe to the topic
topic = 'test-topic'  # Replace with your Kafka topic name
consumer.subscribe([topic])

# API endpoint to store data in MongoDB
api_url = "http://localhost:8000/api/v1/items/"

try:
    print("Listening for messages. Press Ctrl+C to exit.")
    while True:
        msg = consumer.poll(1.0)  # Poll for messages with a 1-second timeout
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                print(f"End of partition reached {msg.topic()} [{msg.partition()}]")
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            # Print the message value
            message = msg.value().decode('utf-8')
            print(f"Received message: {message} from {msg.topic()} [{msg.partition()}]")

            # Parse the message as JSON
            data = json.loads(message)

            # Send the message to the FastAPI endpoint to store in MongoDB
            response = requests.post(api_url, json=data)
            if response.status_code == 201:
                print("Item stored in MongoDB successfully!")
            else:
                print(f"Failed to store item in MongoDB: {response.status_code}")
                print(response.text)
except KeyboardInterrupt:
    print("\nExiting consumer.")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up and close the consumer
    consumer.close()