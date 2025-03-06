# Telco-Edge CDN for Latency-Sensitive Video Streaming



# System design

![System design](images/system_design.png)

# Core Services

## Database CRUD
FastAPI service for video metadata management:

- REST API at /api/v1/items/ for creating and managing video catalog entries
- Stores metadata in MongoDB's videos collection with status tracking
- Exposed on port 8011 with NodePort 30004 for external access

## File Storage Service
Manages video content processing and distribution:

- Handles video uploads with automatic HLS transcoding for streaming
- MinIO integration for scalable object storage
- Synchronizes content between core and edge locations on demand

## Kafka
Event broker for coordinating the distributed CDN:

- Processes cache-miss events from edge locations
- Facilitates content distribution decisions
- Collects analytics data from edge deployments

## MongoDB
NoSQL database for video content metadata:

- Stores structured documents for video properties and availability
- Tracks content locations across the CDN network
- Enables efficient catalog searching and filtering

## Grafana
Real time monitoring with pre-configured dashboards:

|Dashboard           |link|
|MinIo Dashboard     |https://grafana.com/grafana/dashboards/13502-minio-dashboard/|
|MinIo Dashboard     |https://grafana.com/grafana/dashboards/13502-minio-dashboard/|
|Video uploader      |https://github.com/Kludex/fastapi-prometheus-grafana|
|Request controller  |https://github.com/Kludex/fastapi-prometheus-grafana|
|Kafka               |https://grafana.com/grafana/dashboards/18276-kafka-dashboard/|

## Prometheus
Time-series metrics collection:

- Aggregates performance data from all core services
- Powers Grafana visualizations and alerts
- Provides historical metrics for capacity planning

## ingress
Nginx-based service that provides external access to core CDN services:

- Routes external traffic to appropriate core services (database, file storage, etc.)
- Provides unified access point for the core CDN platform
- Handles load balancing across multiple service instances

# core Kubernetes deployment

## Bring up cluster

```bash
kubectl apply -f core/k8s/
```

## Clean cluster

Cluster can be cleaned with script. This script deletes all pods and related configs from kubernetes in one namespace. Default value for 'namespace' is 'default' and core is deployed to 'default' namespace.
```bash
sh clean-k8s-namespace.sh <namespace>
```

## Update kubernetes cluster with new containers

```bash
dockcer compose push  # On development machine

# On kubernetes controller node
git pull
sh core/update_k8s_pods.sh
```

# Edge Services

## Minio
Object storage service deployed at the edge location that caches video content from the core. Provides an S3-compatible API for efficient storage and retrieval of video segments with a web-based dashboard for management.

## Streaming controller
FastAPI service that handles HLS video streaming requests, checking local cache first and retrieving from core when needed. Features include:
- Fast delivery of video manifests and segments
- Cache hit/miss tracking with Prometheus metrics
- Integration with Kafka for event streaming
- Automatic fetch from core storage when content is not cached

## Redis
In-memory data store that tracks file access patterns and caching events. Used for:
- Storing file access timestamps and frequency
- Publishing cache miss events for prediction models
- Supporting real-time decision making for cache management

## Cache controller
Service that orchestrates what gets cached and when, based on:
- Access patterns tracked in Redis
- Communication with AI prediction service via gRPC
- Implementation of cache replacement policies
- Management of cache storage space

## AI cache prediction
gRPC-based service leveraging OpenAI to predict which files will be accessed soon:
- Analyzes access patterns and timestamps
- Processes cache miss events from Kafka
- Returns JSON-based predictions for optimal caching
- Provides intelligence to the caching system

## Ingress
Nginx-based service that routes external traffic to appropriate internal services:
- Provides unified access point (http://localhost)
- Routes traffic to streaming, management, and monitoring services
- Handles TLS termination and request filtering

## Grafana
Visualization platform for monitoring edge performance:
- Custom dashboards for video streaming metrics
- Integration with Prometheus data sources
- Real-time monitoring of cache hit/miss ratios
- Provisioned dashboard for metrics

## Prometheus
Time-series database that collects metrics from all edge services:
- Scrapes custom metrics (cache hits/misses, retrieval times)
- Tracks system resource utilization
- Stores historical performance data
- Powers alerting and visualization

## Prometheus adapter
Translates Prometheus metrics into Kubernetes-native metrics for HPA:
- Enables scaling based on custom metrics (e.g., request rate)
- Integrates with Kubernetes Horizontal Pod Autoscaler
- Allows defining custom scaling rules based on application metrics

This github tutorial has been used as base for prometheus adapter in our deployment:
https://github.com/antonputra/tutorials/tree/main/lessons/073

## Kubernetes for Edge Services

1. Install Prerequisites
   - Install kubectl on your computer
   - Install minikube

2. Start Minikube
```powershell
minikube start
```

3. Enable Addons
```bash
minikube addons enable ingress
minikube addons enable metrics-server
```

4. Deploy Kubernetes Resources
```bash
kubectl apply -f -R k8s/ 
```

5. To Clear and Redeploy (if needed)
```bash
# Delete all resources in k8s directory
kubectl delete -f -R k8s/

# Wait for resources to be fully deleted

# Reapply the configuration
kubectl apply -f -R k8s/
```

6. Open tunnel
```bash
minikube tunnel
```

7. Access Dashboards
   - MinIO Dashboard: ```http://localhost/minio```
   - Grafana Dashboard: ```http://localhost/grafana```
   - Prometheus Dashboard: ```http://localhost/prometheus```


# Testing

## Setup

1. Create and activate a Python virtual environment:
```sh
python -m venv .venv
source .venv/activate 

pip install -r requirements.txt
```

## Run test with docker compose

```bash
# All test cases
pytest -s -v
# invidual test cases
pytest -s -v  test/core/file-storage-service/test_file_storage_service.py
```
## Run test with kubernetes deployment

```bash
# All test cases
TEST_ENV=kubernetes pytest -s -v
# invidual test cases
TEST_ENV=kubernetes pytest -s -v  test/core/file-storage-service/test_file_storage_service.py
```

## Load testing

### Video streaming load testing

locust is used for load testing video streaming. The test_video_streaming.py script implements a realistic approach to load testing streaming services by simulating real viewer behavior:

- Realistic User Simulation: Implements buffer-aware playback patterns typical of video players
- Incremental Load Testing: Gradually increases concurrent users until system degradation (2% failure threshold)
- HLS Protocol Testing: Tests both manifest and segment retrieval
- Detailed Metrics: Captures response times, failure rates, and throughput

### Testing results

Users: 105, RPS: 18.9, Failure Rate: 0.00%
=== TEST COMPLETE ===
Precise saturation point: ~105 users
Total requests: 1250
Total failures: 0
Connection errors: 0

