#!/bin/sh

python3 manage.py collectstatic --noinput
python3 manage.py migrate
python3 manage.py flush --no-input
python3 manage.py loaddata distributors.json
gunicorn composearch.wsgi --timeout 60 --workers 3