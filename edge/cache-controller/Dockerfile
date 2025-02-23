# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY ai_service_pb2_grpc.py .
COPY ai_service_pb2.py .

# Expose port
EXPOSE 5032

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5032"]