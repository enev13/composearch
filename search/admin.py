from typing import ClassVar

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from search import models
from search.tasks import probe_distributors

HEALTH_COLORS = {
    "healthy": "#4caf50",
    "degraded": "#ff9800",
    "failing": "#f44336",
    "unknown": "#9e9e9e",
}


class DistributorStatsInline(admin.TabularInline):
    model = models.DistributorStats
    fields = (
        "status",
        "success_rate",
        "total_attempts",
        "total_successes",
        "consecutive_failures",
        "avg_response_ms",
        "last_attempt_at",
        "last_success_at",
        "last_failure_reason",
        "disabled_by_monitor",
        "updated_at",
    )
    readonly_fields = fields
    extra = 0
    max_num = 0
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


class HealthFilter(SimpleListFilter):
    title = "health"
    parameter_name = "health"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin):
        return (
            ("healthy", "Healthy"),
            ("degraded", "Degraded"),
            ("failing", "Failing"),
            ("unknown", "Unknown"),
        )

    def queryset(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]):
        value = self.value()
        if not value:
            return queryset
        # Status blends a stats-row computation with the missing-row ("unknown")
        # case, so matching is evaluated in Python instead of a DB lookup.
        stats_by_distributor_id = {
            stats.distributor_id: stats
            for stats in models.DistributorStats.objects.filter(distributor__in=queryset)
        }
        matching_ids = [
            distributor.id
            for distributor in queryset
            if self._status(distributor, stats_by_distributor_id) == value
        ]
        return queryset.filter(id__in=matching_ids)

    def _status(self, distributor: models.DistributorSourceModel, stats_by_distributor_id: dict):
        stats = stats_by_distributor_id.get(distributor.id)
        return stats.status if stats is not None else "unknown"


class DistributorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active",
        "health",
        "success_rate",
        "avg_response_ms",
        "last_success_at",
        "consecutive_failures",
        "disabled_by_monitor",
    )
    list_filter = ("active", "stats__disabled_by_monitor", HealthFilter)
    search_fields = ("name",)
    inlines = (DistributorStatsInline,)
    actions: ClassVar[list[str]] = ["activate", "deactivate", "test_now", "reset_stats"]

    @admin.display(description="Health")
    def health(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        status = stats.status if stats is not None else "unknown"
        return format_html(
            '<span style="color: #fff; background-color: {}; '
            'padding: 2px 8px; border-radius: 4px;">{}</span>',
            HEALTH_COLORS[status],
            status.title(),
        )

    @admin.display(description="Success rate")
    def success_rate(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        if stats is None or stats.success_rate is None:
            return "-"
        return f"{stats.success_rate:.0%}"

    @admin.display(description="Avg response")
    def avg_response_ms(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        if stats is None or stats.total_attempts == 0:
            return "-"
        return f"{stats.avg_response_ms:.0f} ms"

    @admin.display(description="Last success")
    def last_success_at(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        return stats.last_success_at if stats is not None else None

    @admin.display(description="Consecutive failures")
    def consecutive_failures(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        return stats.consecutive_failures if stats is not None else 0

    @admin.display(description="Disabled by monitor", boolean=True)
    def disabled_by_monitor(self, distributor: models.DistributorSourceModel):
        stats = getattr(distributor, "stats", None)
        return stats.disabled_by_monitor if stats is not None else False

    @admin.action(description="Activate selected distributors")
    def activate(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        updated = queryset.update(active=True)
        models.DistributorStats.objects.filter(distributor__in=queryset).update(
            consecutive_failures=0, disabled_by_monitor=False
        )
        self.message_user(request, f"Activated {updated} distributor(s).")

    @admin.action(description="Deactivate selected distributors")
    def deactivate(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        updated = queryset.update(active=False)
        self.message_user(request, f"Deactivated {updated} distributor(s).")

    @admin.action(description="Probe selected distributors now")
    def test_now(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        probe_distributors.delay([distributor.id for distributor in queryset])
        self.message_user(request, f"Scheduled a probe for {queryset.count()} distributor(s).")

    @admin.action(description="Reset health statistics")
    def reset_stats(self, request: HttpRequest, queryset: QuerySet[models.DistributorSourceModel]) -> None:
        deleted, _ = models.DistributorStats.objects.filter(distributor__in=queryset).delete()
        self.message_user(request, f"Reset statistics for {deleted} distributor(s).")


admin.site.register(models.DistributorSourceModel, DistributorAdmin)
