import logging
import time

from django.shortcuts import render

from search.search import perform_search

log = logging.getLogger(__name__)


def home_view(request):
    return render(request, "search/index.html")


async def results_view(request):
    start_time = time.time()
    query = request.GET.get("query")
    if query:
        results = await perform_search(query)
    else:
        results = []
    end_time = time.time()
    log.debug(f"Search took {end_time - start_time:.2f} seconds")
    return render(request, "search/results.html", {"results": results, "query": query})
