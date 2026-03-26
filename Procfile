web: gunicorn hrtech.wsgi --bind 0.0.0.0:$PORT --workers 2
worker: celery -A hrtech worker -l INFO -Q default,openai
beat: celery -A hrtech beat -l INFO
