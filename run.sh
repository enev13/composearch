#!/bin/sh
set -e

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py seed_distributors
uvicorn composearch.asgi:application --host 0.0.0.0 --port "${PORT:-8000}"