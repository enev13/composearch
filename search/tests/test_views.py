from unittest.mock import AsyncMock, patch

from django.test import AsyncClient, TestCase


class TestSearchView(TestCase):
    def test_search_view_renders(self):
        response = self.client.get("/search/", {"query": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/results.html")
        self.assertContains(response, "/search/stream/?query=")
        self.assertContains(response, "test")


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
