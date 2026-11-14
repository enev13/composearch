from unittest.mock import AsyncMock, patch

from django.test import TestCase

from composearch.celery import app
from search import tasks
from search.services.stats import TOP_SEARCHES_CACHE_KEY
from search.tasks import probe_distributors, update_top_search_queries


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


class TestProbeDistributors(TestCase):
    @patch("search.tasks.probe_all", new_callable=AsyncMock)
    def test_probe_distributors_passes_distributor_ids(self, mock_probe_all):
        mock_probe_all.return_value = "Probed 2 distributor(s)."

        result = probe_distributors.run([1, 2])

        mock_probe_all.assert_awaited_once_with([1, 2])
        self.assertEqual(result, "Probed 2 distributor(s).")

    @patch("search.tasks.probe_all", new_callable=AsyncMock)
    def test_probe_distributors_probes_all_by_default(self, mock_probe_all):
        mock_probe_all.return_value = "No distributors to probe."

        result = probe_distributors.run()

        mock_probe_all.assert_awaited_once_with(None)
        self.assertEqual(result, "No distributors to probe.")


class TestBeatSchedule(TestCase):
    def test_probe_distributors_runs_every_six_hours(self):
        entry = app.conf.beat_schedule["probe-distributors"]

        self.assertEqual(entry["task"], "search.tasks.probe_distributors")
        self.assertEqual(entry["schedule"].hour, {0, 6, 12, 18})
        self.assertEqual(entry["schedule"].minute, {0})
