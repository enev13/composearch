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
        self.assertContains(response, 'id="search-completed"')


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


class TestHealthView(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertEqual(data["checks"]["cache"], "ok")

    def test_health_reports_browser_state(self):
        response = self.client.get("/health/")

        self.assertIn("browser", response.json()["checks"])

    def test_health_browser_check_degrades_when_manager_missing(self):
        with patch.dict("sys.modules", {"search.browser_manager": None}):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["browser"], "unknown")

    def test_health_is_never_cached(self):
        response = self.client.get("/health/")

        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_health_db_failure_returns_503(self):
        with patch("search.views.connection") as mock_connection:
            mock_connection.cursor.side_effect = Exception("db down")
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "unavailable")
        self.assertEqual(data["checks"]["database"], "unavailable")
        self.assertEqual(data["checks"]["cache"], "ok")

    def test_health_cache_failure_returns_503(self):
        with patch("search.views.cache.get", return_value=None):
            response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "unavailable")
        self.assertEqual(data["checks"]["database"], "ok")
        self.assertEqual(data["checks"]["cache"], "unavailable")


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
