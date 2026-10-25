import logging
import time

from django.shortcuts import render

from search.search import perform_search

log = logging.getLogger(__name__)


def home_view(request):
    return render(request, "search/index.html")


def loading_view(request):
    """
    Renders an intermediate loading page immediately, while the expensive
    search is performed in the background by results_view.
    """
    query = request.GET.get("query", "")
    return render(request, "search/loading.html", {"query": query})


async def results_view(request):
    start_time = time.time()
    query = request.GET.get("query")
    if query:
        results = await perform_search(query)
    else:
        results = []
    end_time = time.time()
    log.debug(f"Search took {end_time - start_time:.2f} seconds")

    if request.GET.get("fragment"):
        template = "search/results_fragment.html"
    else:
        template = "search/results.html"

    return render(request, template, {"results": results, "query": query})
