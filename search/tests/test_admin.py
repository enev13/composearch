from unittest.mock import patch

from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.utils import timezone

from search.admin import DistributorAdmin, DistributorStatsInline, HealthFilter
from search.models import DistributorSourceModel, DistributorStats


def distributor_fields(**overrides) -> dict:
    """Returns valid DistributorSourceModel field values for admin tests."""
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


class AdminTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.distributor = DistributorSourceModel.objects.create(
            **distributor_fields()
        )
        self.model_admin = DistributorAdmin(DistributorSourceModel, admin.site)

    def _request(self):
        request = RequestFactory().post("/admin/")
        request.session = "session"
        request._messages = FallbackStorage(request)
        return request

    def _messages(self, request) -> list[str]:
        return [str(message) for message in request._messages]


class TestDistributorAdminColumns(AdminTestCase):
    def _create_stats(self, **overrides):
        fields = {
            "distributor": self.distributor,
            "total_attempts": 10,
            "total_successes": 10,
            "consecutive_failures": 0,
            "avg_response_ms": 1500.0,
            "disabled_by_monitor": False,
        }
        fields.update(overrides)
        return DistributorStats.objects.create(**fields)

    def test_health_is_unknown_without_stats(self):
        rendered = self.model_admin.health(self.distributor)
        self.assertIn("#9e9e9e", str(rendered))
        self.assertIn("Unknown", str(rendered))

    def test_health_reflects_stats_status(self):
        for status, failures, successes in (
            ("healthy", 0, 10),
            ("degraded", 0, 5),
            ("failing", 5, 5),
        ):
            with self.subTest(status=status):
                DistributorStats.objects.all().delete()
                self._create_stats(
                    consecutive_failures=failures, total_successes=successes
                )
                rendered = self.model_admin.health(self.distributor)
                self.assertIn(
                    {"healthy": "#4caf50", "degraded": "#ff9800", "failing": "#f44336"}[
                        status
                    ],
                    str(rendered),
                )
                self.assertIn(status.title(), str(rendered))

    def test_success_rate_column(self):
        self.assertEqual(self.model_admin.success_rate(self.distributor), "-")
        self._create_stats(total_attempts=10, total_successes=9)
        self.assertEqual(self.model_admin.success_rate(self.distributor), "90%")

    def test_avg_response_ms_column(self):
        self.assertEqual(self.model_admin.avg_response_ms(self.distributor), "-")
        self._create_stats()
        self.assertEqual(self.model_admin.avg_response_ms(self.distributor), "1500 ms")

    def test_stats_passthrough_columns(self):
        last_success_at = timezone.now()
        self._create_stats(
            consecutive_failures=3,
            disabled_by_monitor=True,
            last_success_at=last_success_at,
        )
        self.assertEqual(self.model_admin.last_success_at(self.distributor), last_success_at)
        self.assertEqual(self.model_admin.consecutive_failures(self.distributor), 3)
        self.assertTrue(self.model_admin.disabled_by_monitor(self.distributor))

    def test_stats_passthrough_columns_without_stats(self):
        self.assertIsNone(self.model_admin.last_success_at(self.distributor))
        self.assertEqual(self.model_admin.consecutive_failures(self.distributor), 0)
        self.assertFalse(self.model_admin.disabled_by_monitor(self.distributor))


class TestHealthFilter(AdminTestCase):
    def _filter(self, value):
        request = RequestFactory().get("/")
        params = {"health": [value]} if value else {}
        return HealthFilter(
            request,
            params=params,
            model=DistributorSourceModel,
            model_admin=self.model_admin,
        )

    def test_lookups(self):
        self.assertEqual(
            self._filter(None).lookups(None, self.model_admin),
            (
                ("healthy", "Healthy"),
                ("degraded", "Degraded"),
                ("failing", "Failing"),
                ("unknown", "Unknown"),
            ),
        )

    def test_filters_by_health_status(self):
        healthy = DistributorSourceModel.objects.create(
            **distributor_fields(name="Healthy Shop")
        )
        DistributorStats.objects.create(distributor=healthy, total_attempts=1, total_successes=1)
        # self.distributor has no stats row -> unknown.

        for value, expected in (("healthy", {healthy.pk}), ("unknown", {self.distributor.pk})):
            with self.subTest(value=value):
                filtered = self._filter(value).queryset(None, DistributorSourceModel.objects.all())
                self.assertEqual(set(filtered.values_list("pk", flat=True)), expected)

    def test_returns_queryset_unfiltered_without_value(self):
        filtered = self._filter(None).queryset(None, DistributorSourceModel.objects.all())
        self.assertEqual(
            set(filtered.values_list("pk", flat=True)),
            {self.distributor.pk},
        )


class TestDistributorAdminActions(AdminTestCase):
    def test_activate_resets_stats(self):
        DistributorStats.objects.create(
            distributor=self.distributor, consecutive_failures=3, disabled_by_monitor=True
        )
        self.model_admin.activate(self._request(), DistributorSourceModel.objects.all())
        self.distributor.refresh_from_db()
        stats = DistributorStats.objects.get(distributor=self.distributor)
        self.assertTrue(self.distributor.active)
        self.assertEqual(stats.consecutive_failures, 0)
        self.assertFalse(stats.disabled_by_monitor)

    def test_deactivate(self):
        request = self._request()
        self.model_admin.deactivate(request, DistributorSourceModel.objects.all())
        self.distributor.refresh_from_db()
        self.assertFalse(self.distributor.active)
        self.assertEqual(self._messages(request), ["Deactivated 1 distributor(s)."])

    def test_activate_messages_user(self):
        request = self._request()
        self.model_admin.activate(request, DistributorSourceModel.objects.all())
        self.assertEqual(self._messages(request), ["Activated 1 distributor(s)."])

    def test_test_now_schedules_probes(self):
        DistributorSourceModel.objects.create(**distributor_fields(name="Second Shop"))
        request = self._request()
        with patch("search.admin.probe_distributors") as probe_task:
            self.model_admin.test_now(request, DistributorSourceModel.objects.all())
        probed_ids = probe_task.delay.call_args[0][0]
        self.assertEqual(
            set(probed_ids),
            set(DistributorSourceModel.objects.values_list("pk", flat=True)),
        )
        self.assertEqual(self._messages(request), ["Scheduled a probe for 2 distributor(s)."])

    def test_reset_stats_deletes_stats_rows(self):
        DistributorStats.objects.create(distributor=self.distributor)
        request = self._request()
        self.model_admin.reset_stats(request, DistributorSourceModel.objects.all())
        self.assertFalse(DistributorStats.objects.exists())
        self.assertEqual(self._messages(request), ["Reset statistics for 1 distributor(s)."])


class TestDistributorStatsInline(AdminTestCase):
    def test_inline_is_fully_read_only(self):
        inline = DistributorStatsInline(DistributorStats, admin.site)
        request = RequestFactory().get("/")
        readonly_fields = inline.get_readonly_fields(request, None)
        self.assertEqual(set(readonly_fields), set(inline.fields))
        self.assertIn("status", readonly_fields)
        self.assertIn("success_rate", readonly_fields)
        self.assertFalse(inline.can_delete)
        self.assertEqual(inline.extra, 0)
