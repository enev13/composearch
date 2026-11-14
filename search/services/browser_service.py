import asyncio
import logging
import time

from decouple import config
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

BROWSER_IDLE_TIMEOUT: float = config("BROWSER_IDLE_TIMEOUT", cast=float, default=300)
BROWSER_LAUNCH_ARGS: list[str] = ["--disable-dev-shm-usage"]

MAX_LAUNCH_ATTEMPTS = 3
LAUNCH_BACKOFF_CAP: float = 30
IDLE_POLL_CAP: float = 30

log = logging.getLogger(__name__)


class BrowserManager:
    """
    Owns the single shared Chromium instance of the current process.

    The browser is launched lazily on first use, health-checked before every
    search and shut down after a configurable idle period; the next acquire
    relaunches it. One manager instance is meant to live for the whole
    process (see the module-level `browser_manager` singleton), so all
    state transitions are serialized through a single asyncio lock.
    """

    def __init__(self, idle_timeout: float) -> None:
        self._idle_timeout = idle_timeout
        self._launch_lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._last_used = time.monotonic()
        self._watcher: asyncio.Task | None = None

    async def acquire(self) -> Browser:
        """
        Returns a connected browser, launching it lazily on first use.

        A browser that crashed since the last search is discarded and
        relaunched; failed launches are retried with backoff and raise
        after MAX_LAUNCH_ATTEMPTS attempts (the next acquire starts the
        sequence over).
        """
        async with self._launch_lock:
            if self._browser is not None and not self._browser.is_connected():
                log.info("Browser disconnected; relaunching.")
                await self._close_browser()
            if self._browser is None:
                self._browser = await self._launch()
                self._start_watcher()
            self.touch()
            return self._browser

    async def new_context(
        self, default_timeout_ms: float | None = None
    ) -> BrowserContext:
        """
        Returns a fresh browser context from the shared browser.

        Passing default_timeout_ms also sets the context default timeout.
        """
        browser = await self.acquire()
        context = await browser.new_context()
        if default_timeout_ms is not None:
            context.set_default_timeout(default_timeout_ms)
        self.touch()
        return context

    def touch(self) -> None:
        """
        Records activity, pushing the idle shutdown deadline forward.
        """
        self._last_used = time.monotonic()

    def status(self) -> str:
        """
        Returns the browser state: "running" (connected browser ready),
        "idle" (no browser resident; it will launch on demand) or
        "dead" (resident browser has crashed; the next acquire relaunches).
        """
        if self._browser is None:
            return "idle"
        return "running" if self._browser.is_connected() else "dead"

    async def shutdown(self) -> None:
        """
        Closes the browser, stops the Playwright driver and cancels the
        idle watcher. Idempotent: safe to call multiple times.
        """
        async with self._launch_lock:
            await self._close_browser()
        watcher, self._watcher = self._watcher, None
        if watcher is not None:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
            except Exception:
                log.debug("Idle watcher raised during shutdown.", exc_info=True)
        log.info("Shared browser shut down.")

    async def _launch(self) -> Browser:
        """
        Launches Chromium, retrying with backoff; the launch lock must be
        held by the caller.
        """
        failures = 0
        while True:
            playwright: Playwright | None = None
            try:
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(args=BROWSER_LAUNCH_ARGS)
            except Exception:
                # Do not leak the driver process of a half-finished launch.
                if playwright is not None:
                    try:
                        await playwright.stop()
                    except Exception:
                        log.debug(
                            "Failed to stop the Playwright driver after a launch error.",
                            exc_info=True,
                        )
                failures += 1
                if failures >= MAX_LAUNCH_ATTEMPTS:
                    log.error(f"Browser launch failed after {failures} attempts; giving up.")
                    raise
                delay = min(2.0**failures, LAUNCH_BACKOFF_CAP)
                log.warning(
                    f"Browser launch failed (attempt {failures}); retrying in {delay}s."
                )
                await asyncio.sleep(delay)
                continue
            self._playwright = playwright
            log.info("Launched shared browser.")
            return browser

    def _start_watcher(self) -> None:
        """
        Starts the idle watcher if idle shutdown is enabled; the launch lock
        must be held by the caller.
        """
        if self._idle_timeout <= 0:
            return
        if self._watcher is not None and not self._watcher.done():
            return
        self._watcher = asyncio.create_task(self._watch_idle())

    async def _watch_idle(self) -> None:
        """
        Polls browser inactivity and shuts the browser down once it has not
        been used for the whole idle timeout.
        """
        poll = min(self._idle_timeout / 4, IDLE_POLL_CAP)
        log.debug(f"Browser idle watcher started (poll interval: {poll}s).")
        while True:
            await asyncio.sleep(poll)
            async with self._launch_lock:
                if self._browser is None:
                    continue
                if time.monotonic() - self._last_used >= self._idle_timeout:
                    log.info(
                        f"Shared browser idle for {self._idle_timeout}s; shutting down."
                    )
                    await self._close_browser()

    async def _close_browser(self) -> None:
        """
        Closes the browser and stops the Playwright driver, tolerating
        already-crashed resources; the launch lock must be held by the
        caller.
        """
        browser, self._browser = self._browser, None
        playwright, self._playwright = self._playwright, None
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                log.debug("Error closing the browser.", exc_info=True)
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                log.debug("Error stopping the Playwright driver.", exc_info=True)


# One shared Chromium per process; import this singleton instead of
# constructing a manager so every search reuses the same browser.
browser_manager = BrowserManager(idle_timeout=BROWSER_IDLE_TIMEOUT)