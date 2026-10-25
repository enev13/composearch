from unittest.mock import AsyncMock, patch

from django.test import AsyncClient, TestCase


class TestLoadingView(TestCase):
    def test_loading_view_renders(self):
        response = self.client.get("/search/", {"query": "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/loading.html")
        self.assertContains(response, 'Searching for "test"')

    def test_loading_view_without_query(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/loading.html")


class TestResultsView(TestCase):
    def setUp(self):
        self.async_client = AsyncClient()

    @patch("search.views.perform_search", new_callable=AsyncMock)
    async def test_results_view_ajax_returns_fragment(self, mock_perform_search):
        mock_perform_search.return_value = []
        response = await self.async_client.get(
            "/search/results/",
            {"query": "test", "fragment": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No results found")
        # The fragment has no wrapping <html> document.
        self.assertNotContains(response, "<html")
        mock_perform_search.assert_awaited_once_with("test")

    @patch("search.views.perform_search", new_callable=AsyncMock)
    async def test_results_view_non_ajax_returns_full_page(self, mock_perform_search):
        mock_perform_search.return_value = []
        response = await self.async_client.get("/search/results/", {"query": "test"})
        self.assertEqual(response.status_code, 200)
        # The full page wraps the fragment in a complete HTML document.
        self.assertContains(response, "<html")
        self.assertContains(response, "No results found")
        mock_perform_search.assert_awaited_once_with("test")