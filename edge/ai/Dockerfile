FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_service.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ai_service.proto
COPY main.py .

ENV OPENAI_API_KEY=""

EXPOSE 50051

CMD ["python", "main.py"]
