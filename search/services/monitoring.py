import logging

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from search.models import (
    DISTRIBUTOR_FAILURE_THRESHOLD,
    DistributorSourceModel,
    DistributorStats,
)
from search.services.product import Product

logger = logging.getLogger(__name__)

EMA_ALPHA = 0.2


@sync_to_async
def record_result(
    distributor: DistributorSourceModel,
    success: bool,
    response_ms: float | None,
    reason: str = "",
) -> None:
    """Record a fetch outcome for a distributor.

    Counters use F() expressions so concurrent recordings do not lose updates.
    A run of failures reaching DISTRIBUTOR_FAILURE_THRESHOLD disables the
    distributor (flagging the stats row so re-enabling is visible in admin).
    """
    now = timezone.now()
    with transaction.atomic():
        stats, _ = DistributorStats.objects.select_for_update().get_or_create(distributor=distributor)
        stats.total_attempts = F("total_attempts") + 1
        stats.last_attempt_at = now
        if success:
            stats.total_successes = F("total_successes") + 1
            stats.consecutive_failures = 0
            stats.last_success_at = now
            if response_ms is not None:
                # Exponential moving average of response times.
                stats.avg_response_ms = stats.avg_response_ms * (1 - EMA_ALPHA) + float(response_ms) * EMA_ALPHA
        else:
            stats.consecutive_failures = F("consecutive_failures") + 1
            stats.last_failure_reason = (reason or "")[:256]
        stats.save(
            update_fields=[
                "total_attempts",
                "total_successes",
                "consecutive_failures",
                "avg_response_ms",
                "last_attempt_at",
                "last_success_at",
                "last_failure_reason",
                "updated_at",
            ]
        )
        if success:
            return
        # F() expressions are not evaluated in memory; reload the row for the
        # threshold check.
        stats.refresh_from_db(fields=["consecutive_failures"])
        if stats.consecutive_failures >= DISTRIBUTOR_FAILURE_THRESHOLD and distributor.active:
            stats.disabled_by_monitor = True
            stats.save(update_fields=["disabled_by_monitor", "updated_at"])
            distributor.active = False
            distributor.save(update_fields=["active"])
            logger.warning(
                "Auto-disabled distributor %s after %d consecutive failures (%s).",
                distributor.name,
                stats.consecutive_failures,
                stats.last_failure_reason,
            )


async def record_outcome(
    distributor: DistributorSourceModel,
    product: Product | None,
    response_ms: float | None,
    reason: str = "",
) -> None:
    """Single recording entry point for real fetches and probes.

    Never raises: stat recording must not break a running search.
    """
    try:
        await record_result(distributor, success=product is not None, response_ms=response_ms, reason=reason)
    except Exception:
        logger.warning("Failed to record stats for %s.", distributor.name, exc_info=True)