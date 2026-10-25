import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "composearch.settings")

app = Celery("composearch")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-top-search-queries": {
        "task": "search.tasks.update_top_search_queries",
        "schedule": 300.0,
    },
}
