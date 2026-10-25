from unittest.mock import AsyncMock, patch

from django.test import AsyncClient, TestCase


class TestSearchView(TestCase):
    @patch("search.views.record_query")
    def test_search_view_renders(self, mock_record_query):
        response = self.client.get("/search/", {"query": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/results.html")
        self.assertContains(response, "/search/stream/?query=")
        self.assertContains(response, "test")


class TestHomeView(TestCase):
    @patch("search.views.get_top_search_queries_cached")
    def test_home_view_shows_trending(self, mock_get_top):
        mock_get_top.return_value = [{"query": "resistor", "count": 5}]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/index.html")
        self.assertContains(response, "Trending searches")
        self.assertContains(response, "resistor")


class TestSearchViewRecordsQuery(TestCase):
    @patch("search.views.record_query")
    def test_search_view_records_query(self, mock_record_query):
        response = self.client.get("/search/", {"query": "Hello World"})
        self.assertEqual(response.status_code, 200)
        mock_record_query.assert_called_once_with("Hello World")


class TestSearchFallbackView(TestCase):
    def setUp(self):
        self.async_client = AsyncClient()

    @patch("search.views.perform_search", new_callable=AsyncMock)
    async def test_search_fallback_view_returns_results(self, mock_perform_search):
        mock_perform_search.return_value = []
        response = await self.async_client.get(
            "/search/fallback/",
            {"query": "test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/results_fallback.html")
        self.assertContains(response, "No results found")
        mock_perform_search.assert_awaited_once_with("test")

    async def test_search_fallback_view_without_query(self):
        response = await self.async_client.get("/search/fallback/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/results_fallback.html")
        self.assertContains(response, "No results found")
