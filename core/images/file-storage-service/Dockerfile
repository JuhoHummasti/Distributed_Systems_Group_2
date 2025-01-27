FROM python:3.12-slim

WORKDIR /app

# Copy requirements.txt and install dependencies
COPY src/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# # Copy the protobuf definitions
# COPY ../protobuf_definitions/file-storage-service /app/protobuf_definitions/file-storage-service

# Copy the source code
COPY src/ ./

CMD ["python", "app.py"]