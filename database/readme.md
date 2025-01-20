Create python venv pymongo and fastapi
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start FastAPI:
```
uvicorn database.app:app --reload
```

Test
```
python test.py or go to http://127.0.0.1:8000/docs#/
```