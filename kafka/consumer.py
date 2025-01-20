from confluent_kafka import Consumer, KafkaException, KafkaError

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
            print(f"Received message: {msg.value().decode('utf-8')} from {msg.topic()} [{msg.partition()}]")
except KeyboardInterrupt:
    print("\nExiting consumer.")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up and close the consumer
    consumer.close()
