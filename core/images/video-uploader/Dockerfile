# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY src/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/ ./

# Expose the port the app runs on
EXPOSE 8000

# Define environment variables
ENV MINIO_ENDPOINT=minio:9000
ENV MINIO_ROOT_USER=myaccesskey
ENV MINIO_ROOT_PASSWORD=mysecretkey
ENV KAFKA_BOOTSTRAP_SERVERS=broker-1:29092,broker-2:39092,broker-3:49092

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]