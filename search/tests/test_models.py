from django.test import TestCase

from search.models import (
    DISTRIBUTOR_FAILURE_THRESHOLD,
    DistributorSourceModel,
    DistributorStats,
)


class TestModels(TestCase):
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

    def test_distributor_is_created(self):
        self.assertEqual(self.distributor.name, "TestShop")
        self.assertEqual(self.distributor.base_url, "https://test.com")
        self.assertEqual(self.distributor.search_string, "search?q=%s")
        self.assertEqual(self.distributor.currency, "EUR")
        self.assertEqual(self.distributor.included_vat, 10)
        self.assertEqual(self.distributor.product_name_selector, "#name")
        self.assertEqual(self.distributor.product_url_selector, "#url")
        self.assertEqual(self.distributor.product_picture_url_selector, "#picture")
        self.assertEqual(self.distributor.product_price_selector, "#price")
        self.assertEqual(self.distributor.active, True)
        self.assertIsNone(self.distributor.probe_query)
        self.assertEqual(str(self.distributor), "TestShop (https://test.com)")

    def test_distributor_is_updated(self):
        self.distributor.name = "TestShop2"
        self.distributor.base_url = "https://test2.com"
        self.distributor.search_string = "search2?q=%s"
        self.distributor.currency = "USD"
        self.distributor.included_vat = 15
        self.distributor.product_name_selector = "#name2"
        self.distributor.product_url_selector = "#url2"
        self.distributor.product_picture_url_selector = "#picture2"
        self.distributor.product_price_selector = "#price2"
        self.distributor.active = False
        self.assertEqual(self.distributor.name, "TestShop2")
        self.assertEqual(self.distributor.base_url, "https://test2.com")
        self.assertEqual(self.distributor.search_string, "search2?q=%s")
        self.assertEqual(self.distributor.currency, "USD")
        self.assertEqual(self.distributor.included_vat, 15)
        self.assertEqual(self.distributor.product_name_selector, "#name2")
        self.assertEqual(self.distributor.product_url_selector, "#url2")
        self.assertEqual(self.distributor.product_picture_url_selector, "#picture2")
        self.assertEqual(self.distributor.product_price_selector, "#price2")
        self.assertEqual(self.distributor.active, False)
        self.assertEqual(str(self.distributor), "TestShop2 (https://test2.com) - INACTIVE")

    def test_distributor_is_deleted(self):
        self.distributor.delete()
        self.assertEqual(DistributorSourceModel.objects.count(), 0)

    def test_distributor_is_inactive(self):
        self.distributor.active = False
        self.assertEqual(str(self.distributor), "TestShop (https://test.com) - INACTIVE")

    def test_distributor_is_active(self):
        self.distributor.active = True
        self.assertEqual(str(self.distributor), "TestShop (https://test.com)")


class TestDistributorStats(TestCase):
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
        self.stats = DistributorStats.objects.create(distributor=self.distributor)

    def test_stats_defaults(self):
        self.assertEqual(self.stats.total_attempts, 0)
        self.assertEqual(self.stats.total_successes, 0)
        self.assertEqual(self.stats.consecutive_failures, 0)
        self.assertEqual(self.stats.avg_response_ms, 0.0)
        self.assertIsNone(self.stats.last_attempt_at)
        self.assertIsNone(self.stats.last_success_at)
        self.assertEqual(self.stats.last_failure_reason, "")
        self.assertFalse(self.stats.disabled_by_monitor)

    def test_stats_str(self):
        self.assertEqual(str(self.stats), "TestShop stats")

    def test_success_rate_with_no_attempts(self):
        self.assertIsNone(self.stats.success_rate)
        self.assertEqual(self.stats.status, "unknown")

    def test_success_rate(self):
        self.stats.total_attempts = 10
        self.stats.total_successes = 7
        self.assertAlmostEqual(self.stats.success_rate, 0.7)

    def test_success_rate_full(self):
        self.stats.total_attempts = 10
        self.stats.total_successes = 10
        self.assertAlmostEqual(self.stats.success_rate, 1.0)
        self.assertEqual(self.stats.status, "healthy")

    def test_status_failing(self):
        self.stats.total_attempts = 5
        self.stats.total_successes = 0
        self.stats.consecutive_failures = DISTRIBUTOR_FAILURE_THRESHOLD
        self.assertEqual(self.stats.status, "failing")

    def test_status_degraded(self):
        self.stats.total_attempts = 5
        self.stats.total_successes = 3
        self.stats.consecutive_failures = 2
        self.assertEqual(self.stats.status, "degraded")

    def test_status_healthy_below_min_attempts(self):
        self.stats.total_attempts = 3
        self.stats.total_successes = 1
        self.stats.consecutive_failures = 1
        self.assertEqual(self.stats.status, "healthy")

    def test_status_healthy(self):
        self.stats.total_attempts = 5
        self.stats.total_successes = 5
        self.stats.consecutive_failures = 0
        self.assertEqual(self.stats.status, "healthy")

    def test_stats_cascade_delete(self):
        self.distributor.delete()
        self.assertEqual(DistributorStats.objects.count(), 0)
