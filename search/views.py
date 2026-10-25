from django.shortcuts import render

from search.search import perform_search


def home_view(request):
    return render(request, "search/index.html")


def search_view(request):
    query = request.GET.get("query", "")
    return render(request, "search/results.html", {"query": query})


async def search_fallback_view(request):
    query = request.GET.get("query")
    results = await perform_search(query) if query else []
    return render(
        request,
        "search/results_fallback.html",
        {"results": results, "query": query},
    )
