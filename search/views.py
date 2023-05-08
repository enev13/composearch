from django.shortcuts import render

from search.search import perform_search


def home_view(request):
    return render(request, "search/index.html")


def results_view(request):
    query = request.GET.get("query")
    results = perform_search(query)
    return render(request, "search/results.html", {"results": results})
