import unittest
import subprocess
import time
import logging
from confluent_kafka import Producer, Consumer, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BROKER_LIST = 'localhost:29092,localhost:39092,localhost:49092'
TEST_TOPIC = 'test-topic'

def create_topic(topic_name):
    admin_client = AdminClient({'bootstrap.servers': BROKER_LIST})
    topic = NewTopic(topic_name, num_partitions=1, replication_factor=3)
    fs = admin_client.create_topics([topic])
    # Wait for topic creation to complete
    fs[topic_name].result()
        
def get_leader_broker(topic, partition=0):
    """Retrieve the leader broker for a given topic and partition."""
    admin_conf = {'bootstrap.servers': BROKER_LIST}
    admin_client = AdminClient(admin_conf)

    metadata = admin_client.list_topics(timeout=10)
    if topic not in metadata.topics:
        raise RuntimeError(f"Topic '{topic}' not found.")
    
    partition_metadata = metadata.topics[topic].partitions[partition]
    return partition_metadata.leader

# Helper to produce messages
def produce_message(message, retries=5):
    conf = {'bootstrap.servers': BROKER_LIST, 'client.id': 'test-producer', 'retries': retries}
    producer = Producer(conf)

    def delivery_report(err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            raise RuntimeError(f"Message delivery failed: {err}")
        else:
            logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    logger.info(f"Producing message: {message}")
    producer.produce(TEST_TOPIC, value=message, callback=delivery_report)
    producer.flush()

# Helper to consume messages
def consume_messages(timeout=10, num_messages=1):
    conf = {
        'bootstrap.servers': BROKER_LIST,
        'group.id': 'test-consumer-group',
        'auto.offset.reset': 'earliest',
    }
    consumer = Consumer(conf)
    consumer.subscribe([TEST_TOPIC])
    messages = []
    start_time = time.time()
    logger.info("Consuming messages...")
    while len(messages) < num_messages and time.time() - start_time < timeout:
        msg = consumer.poll(1.0)
        if msg and not msg.error():
            messages.append(msg.value().decode('utf-8'))
            logger.info(f"Received message: {msg.value().decode('utf-8')}")
    consumer.close()
    return messages

class TestKafkaCluster(unittest.TestCase):
    def setUp(self):
        logger.info("Setting up Kafka cluster...")
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        time.sleep(10)
        logger.info("Kafka cluster is up.")

    def tearDown(self):
        logger.info("Restarting Kafka cluster for clean slate...")
        subprocess.run(["docker-compose", "down"], check=True)
        time.sleep(5)
        logger.info("Kafka cluster has been restarted.")

    def test_normal_operation(self):
        logger.info("Testing normal operation...")
        produce_message("Test message 1")
        messages = consume_messages()
        self.assertIn("Test message 1", messages)
        logger.info("Normal operation test passed.")

    def test_broker_failure(self):
        logger.info("Testing broker failure tolerance...")
        subprocess.run(["docker", "stop", "broker-1"], check=True)
        logger.warning("Broker-1 stopped.")
        time.sleep(5)

        produce_message("Test message 2")
        messages = consume_messages()
        self.assertIn("Test message 2", messages)
        logger.info("Broker failure test passed.")

        subprocess.run(["docker", "start", "broker-1"], check=True)
        logger.info("Broker-1 restarted.")
        time.sleep(5)

    def test_leader_failover(self):
        # Ensure the topic exists before checking the leader
        logger.info("Creating topic if not exists...")
        create_topic(TEST_TOPIC)

        logger.info("Testing leader failover...")
        subprocess.run(["docker", "stop", "broker-2"], check=True)
        logger.warning("Broker-2 stopped.")
        time.sleep(5)

        produce_message("Test message 3")
        messages = consume_messages()
        self.assertIn("Test message 3", messages)

        leader_broker = get_leader_broker(TEST_TOPIC)
        logger.info(f"Current leader broker after failover: {leader_broker}")

        logger.info("Leader failover test passed.")

        subprocess.run(["docker", "start", "broker-2"], check=True)
        logger.info("Broker-2 restarted.")
        time.sleep(5)

    def test_retry_mechanism(self):
        logger.info("Testing producer retry mechanism...")
        subprocess.run(["docker", "stop", "broker-1", "broker-2", "broker-3"], check=True)
        logger.warning("All brokers stopped.")
        time.sleep(5)

        with self.assertRaises(RuntimeError):
            produce_message("Test message 4", retries=2)
        logger.info("Producer retry test passed for failure scenario.")

        subprocess.run(["docker", "start", "broker-1", "broker-2", "broker-3"], check=True)
        logger.info("All brokers restarted.")
        time.sleep(10)

        produce_message("Test message 5")
        messages = consume_messages()
        self.assertIn("Test message 5", messages)
        logger.info("Producer retry test passed for recovery scenario.")

    def test_consumer_on_rebalance(self):
        logger.info("Testing consumer rebalance...")
        subprocess.run(["docker", "stop", "broker-3"], check=True)
        logger.warning("Broker-3 stopped.")
        time.sleep(5)

        produce_message("Test message 6")
        messages = consume_messages()
        self.assertIn("Test message 6", messages)
        logger.info("Consumer rebalance test passed.")

        subprocess.run(["docker", "start", "broker-3"], check=True)
        logger.info("Broker-3 restarted.")
        time.sleep(5)

if __name__ == "__main__":
    logger.info("Starting Kafka cluster tests...")
    unittest.main()
