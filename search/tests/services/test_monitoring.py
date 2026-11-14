from unittest.mock import patch

from django.test import TestCase

from search.models import (
    DISTRIBUTOR_FAILURE_THRESHOLD,
    DistributorSourceModel,
    DistributorStats,
)
from search.services.monitoring import EMA_ALPHA, record_outcome, record_result

from ..fixtures.products import sample_product


class TestMonitoring(TestCase):
    def setUp(self) -> None:
        self.distributor = DistributorSourceModel.objects.create(
            name="TestShop",
            base_url="https://test.com",
            search_string="search?q=%s",
            currency="EUR",
            included_vat=10,
            product_name_selector="#name",
            product_url_selector="#url",
            product_picture_url_selector="#picture",
            product_price_selector="#price",
            active=True,
        )

    async def _stats(self) -> DistributorStats:
        return await DistributorStats.objects.aget(distributor=self.distributor)

    async def test_success_counters(self):
        await record_result(self.distributor, success=True, response_ms=100.0)
        stats = await self._stats()
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 1)
        self.assertEqual(stats.consecutive_failures, 0)
        self.assertEqual(stats.last_failure_reason, "")
        self.assertIsNotNone(stats.last_attempt_at)
        self.assertIsNotNone(stats.last_success_at)
        self.assertGreater(stats.avg_response_ms, 0)

    async def test_failure_counters(self):
        await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        stats = await self._stats()
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.consecutive_failures, 1)
        self.assertEqual(stats.last_failure_reason, "timeout")
        self.assertIsNone(stats.last_success_at)
        self.assertEqual(stats.avg_response_ms, 0.0)

    async def test_ema_response_time(self):
        await record_result(self.distributor, success=True, response_ms=100.0)
        stats = await self._stats()
        self.assertAlmostEqual(stats.avg_response_ms, 100.0 * EMA_ALPHA)
        await record_result(self.distributor, success=True, response_ms=100.0)
        stats = await self._stats()
        expected = 100.0 * EMA_ALPHA * (1 - EMA_ALPHA) + 100.0 * EMA_ALPHA
        self.assertAlmostEqual(stats.avg_response_ms, expected)

    async def test_success_resets_consecutive_failures(self):
        await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        stats = await self._stats()
        self.assertEqual(stats.consecutive_failures, 2)
        await record_result(self.distributor, success=True, response_ms=50.0)
        stats = await self._stats()
        self.assertEqual(stats.consecutive_failures, 0)
        self.assertEqual(stats.total_attempts, 3)
        self.assertEqual(stats.total_successes, 1)
        # The last failure reason is kept as history.
        self.assertEqual(stats.last_failure_reason, "timeout")

    async def test_auto_disable_at_threshold(self):
        with self.assertLogs("search.services.monitoring", level="WARNING"):
            for _ in range(DISTRIBUTOR_FAILURE_THRESHOLD):
                await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        stats = await self._stats()
        self.assertEqual(stats.consecutive_failures, DISTRIBUTOR_FAILURE_THRESHOLD)
        self.assertTrue(stats.disabled_by_monitor)
        await self.distributor.arefresh_from_db()
        self.assertFalse(self.distributor.active)

    async def test_below_threshold_stays_active(self):
        for _ in range(DISTRIBUTOR_FAILURE_THRESHOLD - 1):
            await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        stats = await self._stats()
        self.assertEqual(stats.consecutive_failures, DISTRIBUTOR_FAILURE_THRESHOLD - 1)
        self.assertFalse(stats.disabled_by_monitor)
        await self.distributor.arefresh_from_db()
        self.assertTrue(self.distributor.active)

    async def test_already_inactive_distributor_not_flagged(self):
        self.distributor.active = False
        await self.distributor.asave()
        for _ in range(DISTRIBUTOR_FAILURE_THRESHOLD):
            await record_result(self.distributor, success=False, response_ms=None, reason="timeout")
        stats = await self._stats()
        self.assertEqual(stats.consecutive_failures, DISTRIBUTOR_FAILURE_THRESHOLD)
        self.assertFalse(stats.disabled_by_monitor)

    async def test_record_outcome_success(self):
        await record_outcome(self.distributor, sample_product, 100.0)
        stats = await self._stats()
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 1)
        self.assertEqual(stats.consecutive_failures, 0)

    async def test_record_outcome_failure(self):
        await record_outcome(self.distributor, None, None, reason="parse_error")
        stats = await self._stats()
        self.assertEqual(stats.total_attempts, 1)
        self.assertEqual(stats.total_successes, 0)
        self.assertEqual(stats.last_failure_reason, "parse_error")

    async def test_record_outcome_never_raises(self):
        with patch("search.services.monitoring.record_result", side_effect=Exception("boom")):
            await record_outcome(self.distributor, sample_product, 100.0)