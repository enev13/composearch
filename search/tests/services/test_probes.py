from unittest.mock import AsyncMock, patch

from django.test import TestCase

from search.models import DistributorSourceModel, DistributorStats
from search.services.fetcher import BROWSER_TIMEOUT
from search.services.probes import probe_all, probe_distributor

from ..fixtures.playwright import MockBrowserManager, MockContext


def distributor_fields(**overrides) -> dict:
    """
    Returns DistributorSourceModel fields for a distributor whose search
    result pages the playwright mocks can serve.
    """
    fields = {
        "name": "TestShop",
        "base_url": "https://test.com/",
        "search_string": "search?q=%s",
        "currency": "EUR",
        "included_vat": 10,
        "product_name_selector": "#name",
        "product_url_selector": "a",
        "product_picture_url_selector": "img",
        "product_price_selector": "div > span",
        "active": True,
        "probe_query": "test",
    }
    fields.update(overrides)
    return fields


class TestProbeDistributor(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.distributor = DistributorSourceModel.objects.create(
            **distributor_fields()
        )

    async def _stats(self) -> DistributorStats | None:
        return await DistributorStats.objects.filter(
            distributor=self.distributor
        ).afirst()

    async def test_records_success(self):
        await probe_distributor(MockContext(), self.distributor)

        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 1)
        self.assertEqual(stats.consecutive_failures, 0)
        self.assertEqual(stats.last_failure_reason, "")
        self.assertGreater(stats.avg_response_ms, 0)
        self.assertIsNotNone(stats.last_attempt_at)
        self.assertIsNotNone(stats.last_success_at)

    async def test_skips_distributor_without_query(self):
        self.distributor.probe_query = None
        await self.distributor.asave()

        with self.assertLogs("search.services.probes", level="WARNING"), patch(
            "search.services.probes.PROBE_DEFAULT_QUERY", ""
        ):
            await probe_distributor(MockContext(), self.distributor)

        self.assertIsNone(await self._stats())

    async def test_falls_back_to_default_query(self):
        self.distributor.probe_query = None
        await self.distributor.asave()

        with patch("search.services.probes.PROBE_DEFAULT_QUERY", "test"):
            await probe_distributor(MockContext(), self.distributor)

        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_successes, 1)

    async def test_normalizes_query(self):
        self.distributor.probe_query = "TEST"
        await self.distributor.asave()

        await probe_distributor(MockContext(), self.distributor)

        stats = await self._stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_successes, 1)


class TestProbeAll(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.distributor = DistributorSourceModel.objects.create(
            **distributor_fields()
        )
        patcher = patch(
            "search.services.probes.BrowserManager", MockBrowserManager
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    async def _stats_for(self, distributor) -> DistributorStats | None:
        return await DistributorStats.objects.filter(
            distributor=distributor
        ).afirst()

    async def test_probes_each_active_distributor(self):
        summary = await probe_all()

        self.assertEqual(summary, "Probed 1 distributor(s).")
        stats = await self._stats_for(self.distributor)
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 1)

    async def test_restricts_to_given_ids(self):
        second = await DistributorSourceModel.objects.acreate(
            **distributor_fields(name="TestShop2", probe_query="test2")
        )

        summary = await probe_all([self.distributor.id])

        self.assertEqual(summary, "Probed 1 distributor(s).")
        self.assertIsNotNone(await self._stats_for(self.distributor))
        self.assertIsNone(await self._stats_for(second))

    async def test_skips_inactive_distributors(self):
        second = await DistributorSourceModel.objects.acreate(
            **distributor_fields(name="TestShop2", active=False)
        )

        summary = await probe_all()

        self.assertEqual(summary, "Probed 1 distributor(s).")
        self.assertIsNotNone(await self._stats_for(self.distributor))
        self.assertIsNone(await self._stats_for(second))

    async def test_reports_when_nothing_to_probe(self):
        await DistributorSourceModel.objects.filter(
            pk=self.distributor.pk
        ).aupdate(active=False)

        summary = await probe_all()

        self.assertEqual(summary, "No distributors to probe.")

    async def test_does_not_touch_search_cache(self):
        with patch("search.services.fetcher.cache") as mock_cache:
            await probe_all([self.distributor.id])

        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    async def test_shares_one_context_and_shuts_browser_down(self):
        with patch("search.services.probes.BrowserManager") as mock_manager_cls:
            manager = mock_manager_cls.return_value
            manager.new_context = AsyncMock(return_value=MockContext())
            manager.shutdown = AsyncMock()

            summary = await probe_all([self.distributor.id])

        self.assertEqual(summary, "Probed 1 distributor(s).")
        mock_manager_cls.assert_called_once_with(idle_timeout=0)
        manager.new_context.assert_awaited_once_with(
            default_timeout_ms=BROWSER_TIMEOUT
        )
        manager.shutdown.assert_awaited_once()
