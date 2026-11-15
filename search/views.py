import logging

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from search.services.search_service import perform_search
from search.services.stats import get_top_search_queries_cached, record_query

logger = logging.getLogger(__name__)


def home_view(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "search/index.html",
        {"top_queries": get_top_search_queries_cached()},
    )


def search_view(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("query", "")
    record_query(query)
    return render(request, "search/results.html", {"query": query})


async def search_fallback_view(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("query")
    results = await perform_search(query) if query else []
    return render(
        request,
        "search/results_fallback.html",
        {"results": results, "query": query},
    )


@never_cache
def health_view(request: HttpRequest) -> JsonResponse:
    """Liveness probe backing /health/ and the compose web healthcheck."""
    checks: dict[str, object] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        logger.warning("Health check: database unavailable", exc_info=True)
        checks["database"] = "unavailable"

    try:
        cache.set("healthcheck", "ok", timeout=10)
        checks["cache"] = "ok" if cache.get("healthcheck") == "ok" else "unavailable"
    except Exception:
        logger.warning("Health check: cache unavailable", exc_info=True)
        checks["cache"] = "unavailable"

    # Informational only: report the browser pool state when the
    # browser-lifecycle plan adds search.browser_manager; degrade to
    # "unknown" until then. Never launches a browser.
    try:
        from search import browser_manager

        checks["browser"] = browser_manager.status()
    except ImportError:
        checks["browser"] = "unknown"

    healthy = checks.get("database") == "ok" and checks.get("cache") == "ok"
    return JsonResponse(
        {"status": "ok" if healthy else "unavailable", "checks": checks},
        status=200 if healthy else 503,
    )
