import asyncio
import logging
from urllib.parse import quote_plus, urljoin

from asgiref.sync import sync_to_async
from decouple import config
from playwright.async_api import BrowserContext

from search.models import DistributorSourceModel
from search.services.browser_service import BrowserManager
from search.services.fetcher import (
    BROWSER_TIMEOUT,
    SEARCH_CONCURRENCY_LIMIT,
    _fetch_and_parse,
)
from search.services.monitoring import record_outcome

PROBE_DEFAULT_QUERY: str = config("PROBE_DEFAULT_QUERY", default="")

log = logging.getLogger(__name__)


async def probe_distributor(
    context: BrowserContext,
    distributor: DistributorSourceModel,
    semaphore: asyncio.Semaphore | None = None,
) -> None:
    """
    Takes a BrowserContext, a DistributorSourceModel and an optional
    semaphore capping concurrent fetches.

    Fetches the distributor's probe query (falling back to the configured
    default) and records the outcome in its DistributorStats row.
    Distributors without any probe query are skipped.
    """
    query = (distributor.probe_query or PROBE_DEFAULT_QUERY).strip()
    if not query:
        log.warning(
            "Skipping probe for %s: no probe_query and no PROBE_DEFAULT_QUERY.",
            distributor.name,
        )
        return
    query = quote_plus(query.encode("utf-8").strip().lower())
    url = urljoin(
        distributor.base_url, distributor.search_string.replace("%s", query)
    )
    product, _, _, response_ms, reason = await _fetch_and_parse(
        context, distributor, url, semaphore=semaphore
    )
    await record_outcome(distributor, product, response_ms, reason)


@sync_to_async
def _probe_targets(distributor_ids: list[int] | None) -> list[DistributorSourceModel]:
    """
    Returns the active distributors a probe run should cover, narrowed to
    the given ids when provided.
    """
    distributors = DistributorSourceModel.objects.filter(active=True)
    if distributor_ids:
        distributors = distributors.filter(id__in=distributor_ids)
    return list(distributors)


async def probe_all(distributor_ids: list[int] | None = None) -> str:
    """
    Probes active distributors (all of them when distributor_ids is None)
    in one shared browser context and returns a one-line summary for the
    task result.
    """
    distributors = await _probe_targets(distributor_ids)
    if not distributors:
        return "No distributors to probe."

    # The Celery task runs each probe_all() in its own asyncio.run() loop, so
    # loop-bound primitives (the semaphore, the browser manager) are created
    # per run; idle_timeout=0 disables the manager's idle watcher.
    semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY_LIMIT)
    manager = BrowserManager(idle_timeout=0)
    context = None
    try:
        context = await manager.new_context(default_timeout_ms=BROWSER_TIMEOUT)
        probes = [
            probe_distributor(context, distributor, semaphore)
            for distributor in distributors
        ]
        results = await asyncio.gather(*probes, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                log.warning("Probe raised.", exc_info=result)
        return f"Probed {len(distributors)} distributor(s)."
    finally:
        if context is not None:
            try:
                await context.close()
            except Exception:
                log.debug("Error closing the probe context.", exc_info=True)
        await manager.shutdown()
