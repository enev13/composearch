from django.shortcuts import render

from search.search import perform_search
from search.stats import get_top_search_queries_cached, record_query


def home_view(request):
    return render(
        request,
        "search/index.html",
        {"top_queries": get_top_search_queries_cached()},
    )


def search_view(request):
    query = request.GET.get("query", "")
    record_query(query)
    return render(request, "search/results.html", {"query": query})


async def search_fallback_view(request):
    query = request.GET.get("query")
    results = await perform_search(query) if query else []
    return render(
        request,
        "search/results_fallback.html",
        {"results": results, "query": query},
    )
