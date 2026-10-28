"""
ASGI config for composearch project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "composearch.settings")

django_asgi_app = get_asgi_application()

# Imported after Django setup because the consumer imports models.
from search.consumers import SearchStreamConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": URLRouter(
            [
                re_path(r"^search/stream/$", SearchStreamConsumer.as_asgi()),
                re_path(r"", django_asgi_app),
            ]
        ),
    }
)
