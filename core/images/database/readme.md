Create python venv pymongo and fastapi
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download docker if you dont have it
```
https://www.docker.com/
```

Run MongoDB with docker
```
docker run -d -p 27017:27017 --name mongodb mongo
```

Stop docker
```
docker stop  mongodb
```

Start FastAPI:
```
uvicorn database.app:app --reload
```

Test
```
python test.py or go to http://127.0.0.1:8000/docs#/
```