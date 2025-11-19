web: gunicorn flask_app:app --bind 0.0.0.0:$PORT
api: uvicorn api:app --host 0.0.0.0 --port $PORT
worker: celery -A celery_app worker --loglevel=info

