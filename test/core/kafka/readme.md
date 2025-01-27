
Create python venv for producer and consumer
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start kafka containers:
```
docker compose up -d
```

Stop kafka containers
```
docker compose down
```

Run tests
```
python -m unittest test_kafka_cluster.py
```