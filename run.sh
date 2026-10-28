#!/bin/sh

python3 manage.py collectstatic --noinput
python3 manage.py migrate
python3 manage.py flush --no-input
python3 manage.py loaddata distributors.json
uvicorn composearch.asgi:application --host 0.0.0.0 --port 8000 --workers 3