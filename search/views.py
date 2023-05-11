from django.shortcuts import render

from search.search import perform_search


async def search_async(query, loop):
    return await perform_search(query, loop)


def home_view(request):
    return render(request, "search/index.html")


async def results_view(request):
    query = request.GET.get("query")
    if query:
        results = await perform_search(query)
    else:
        results = []

    return render(request, "search/results.html", {"results": results, "query": query})
