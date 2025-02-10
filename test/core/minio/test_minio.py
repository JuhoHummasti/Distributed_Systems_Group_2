import pytest
from minio import Minio
from minio.error import S3Error
import sys
from pathlib import Path

# Add test directory to Python path
test_dir = str(Path(__file__).parent.parent.parent)
if test_dir not in sys.path:
    sys.path.append(test_dir)

from utils.port_forward import PortForwarder

# MinIO service configuration
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "myaccesskey"  # Replace with actual access key
MINIO_SECRET_KEY = "mysecretkey"  # Replace with actual secret key
BUCKET_NAME = "test-bucket"

@pytest.fixture(scope="module")
def minio_client():
    # Initialize MinIO client
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    return client

@pytest.fixture(scope="session", autouse=True)
def port_forwarder():
    forwarder = PortForwarder()
    # Add all required services
    forwarder.start_port_forward("minio", 9000, 9000)
    
    yield forwarder
    
    forwarder.cleanup()

def test_minio_connection(minio_client):
    # Test connection to MinIO server
    try:
        # List buckets to check connection
        buckets = minio_client.list_buckets()
        assert buckets is not None
    except S3Error as err:
        pytest.fail(f"Failed to connect to MinIO: {err}")

def test_minio_operations(minio_client):
    # Test bucket creation
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
        assert minio_client.bucket_exists(BUCKET_NAME)
    except S3Error as err:
        pytest.fail(f"Failed to create bucket: {err}")

    # Test bucket removal
    try:
        if minio_client.bucket_exists(BUCKET_NAME):
            minio_client.remove_bucket(BUCKET_NAME)
        assert not minio_client.bucket_exists(BUCKET_NAME)
    except S3Error as err:
        pytest.fail(f"Failed to remove bucket: {err}")
