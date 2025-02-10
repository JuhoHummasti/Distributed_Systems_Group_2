Create a Docker network for Prometheus and Grafana:
```
docker network create monitoring
```

Run prometheus and grafana with docker
```
docker-compose up -d
```

Stop docker
```
docker-compose down
```