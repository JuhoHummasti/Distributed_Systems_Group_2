from minio import Minio
from minio.error import S3Error

# Initialize the MinIO client
client = Minio(
    "localhost:9000",
    access_key="myaccesskey",
    secret_key="mysecretkey",
    secure=False
)

# Create a bucket
bucket_name = "mybucket"
try:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' created successfully")
    else:
        print(f"Bucket '{bucket_name}' already exists")
except S3Error as e:
    print(f"Error occurred: {e}")

# Upload a file
try:
    client.fput_object(
        "mybucket", "myobject", "testfile.txt"
    )
    print("File uploaded successfully")
except S3Error as e:
    print(f"Error occurred: {e}")

# Download a file
try:
    client.fget_object(
        bucket_name, "myobject", "downloaded_testfile.txt"
    )
    print("File downloaded successfully")
except S3Error as e:
    print(f"Error occurred: {e}")