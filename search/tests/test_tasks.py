from unittest.mock import patch

from django.test import TestCase

from search import tasks
from search.stats import TOP_SEARCHES_CACHE_KEY
from search.tasks import update_top_search_queries


class TestUpdateTopSearchQueries(TestCase):
    @patch("search.tasks.cache")
    @patch("search.tasks.get_top_queries")
    def test_update_top_search_queries(self, mock_get_top, mock_cache):
        sample_list = [{"query": "resistor", "count": 7}]
        mock_get_top.return_value = sample_list

        result = update_top_search_queries.run()

        mock_get_top.assert_called_once_with(tasks.TOP_SEARCHES_LIMIT)
        mock_cache.set.assert_called_once_with(
            TOP_SEARCHES_CACHE_KEY, sample_list, timeout=None
        )
        self.assertEqual(result, sample_list)
