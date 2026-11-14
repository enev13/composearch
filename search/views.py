from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from search.services.search_service import perform_search
from search.services.stats import get_top_search_queries_cached, record_query


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
