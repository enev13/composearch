from unittest.mock import MagicMock, patch

from django.test import TestCase

from search import stats
from search.stats import (
    REDIS_SORTED_SET_KEY,
    TOP_SEARCHES_CACHE_KEY,
    get_top_queries,
    get_top_search_queries_cached,
    record_query,
)


class TestRecordQuery(TestCase):
    @patch("search.stats._get_redis")
    def test_record_query_normalizes_and_calls_zincrby(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        record_query("  Hello WORLD ")

        mock_get_redis.assert_called_once()
        mock_redis.zincrby.assert_called_once_with(
            REDIS_SORTED_SET_KEY, 1, "hello world"
        )

    @patch("search.stats._get_redis")
    def test_record_query_empty_does_not_call_zincrby(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        record_query("   ")
        mock_redis.zincrby.assert_not_called()

        record_query("")
        mock_redis.zincrby.assert_not_called()


class TestGetTopQueries(TestCase):
    @patch("search.stats._get_redis")
    def test_get_top_queries_parses_zrevrange(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.zrevrange.return_value = [(b"foo", 5.0), (b"bar", 3.0)]
        mock_get_redis.return_value = mock_redis

        result = get_top_queries()

        self.assertEqual(
            result,
            [{"query": "foo", "count": 5}, {"query": "bar", "count": 3}],
        )
        mock_redis.zrevrange.assert_called_once_with(
            REDIS_SORTED_SET_KEY, 0, stats.TOP_SEARCHES_LIMIT - 1, withscores=True
        )


class TestGetTopSearchQueriesCached(TestCase):
    @patch("search.stats.get_top_queries")
    @patch("search.stats.cache")
    def test_returns_cached_without_recomputing(self, mock_cache, mock_get_top):
        mock_cache.get.return_value = [{"query": "cached", "count": 9}]

        result = get_top_search_queries_cached()

        self.assertEqual(result, [{"query": "cached", "count": 9}])
        mock_cache.get.assert_called_once_with(TOP_SEARCHES_CACHE_KEY)
        mock_get_top.assert_not_called()

    @patch("search.stats.get_top_queries")
    @patch("search.stats.cache")
    def test_cache_miss_computes_and_sets(self, mock_cache, mock_get_top):
        mock_cache.get.return_value = None
        sample = [{"query": "a", "count": 1}]
        mock_get_top.return_value = sample

        result = get_top_search_queries_cached()

        self.assertEqual(result, sample)
        mock_cache.get.assert_called_once_with(TOP_SEARCHES_CACHE_KEY)
        mock_get_top.assert_called_once()
        mock_cache.set.assert_called_once_with(
            TOP_SEARCHES_CACHE_KEY, sample, timeout=None
        )
