from decouple import config
from django.db import models

# Lives here (not in search.services.monitoring) to avoid a circular import:
# DistributorStats.status needs it and monitoring imports the models.
DISTRIBUTOR_FAILURE_THRESHOLD: int = config("DISTRIBUTOR_FAILURE_THRESHOLD", cast=int, default=5)


class DistributorSourceModel(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    base_url = models.URLField(max_length=256, null=False, blank=False)
    search_string = models.CharField(max_length=1024, null=False, blank=False)
    currency = models.CharField(max_length=3, null=False, blank=False)
    included_vat = models.PositiveIntegerField(default=0)
    product_name_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_url_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_picture_url_selector = models.CharField(max_length=1024, null=False, blank=False)
    product_price_selector = models.CharField(max_length=1024, null=False, blank=False)
    active = models.BooleanField(default=True)
    probe_query = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text="Search term for selector health probes; falls back to PROBE_DEFAULT_QUERY.",
    )

    def __str__(self):
        return f"{self.name} ({self.base_url}){' - INACTIVE' if not self.active else ''}"


class DistributorStats(models.Model):
    distributor = models.OneToOneField(
        DistributorSourceModel,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    total_attempts = models.PositiveIntegerField(default=0)
    total_successes = models.PositiveIntegerField(default=0)
    consecutive_failures = models.PositiveIntegerField(default=0)
    avg_response_ms = models.FloatField(default=0.0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_reason = models.CharField(max_length=256, blank=True, default="")
    disabled_by_monitor = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.distributor.name} stats"

    @property
    def success_rate(self) -> float | None:
        if self.total_attempts == 0:
            return None
        return self.total_successes / self.total_attempts

    @property
    def status(self) -> str:
        if self.total_attempts == 0:
            return "unknown"
        if self.consecutive_failures >= DISTRIBUTOR_FAILURE_THRESHOLD:
            return "failing"
        success_rate = self.success_rate
        if self.total_attempts >= 5 and success_rate is not None and success_rate < 0.8:
            return "degraded"
        return "healthy"
