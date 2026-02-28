from __future__ import annotations

import logging
import os
from pathlib import Path

from playwright.async_api import Browser, Page, Playwright, async_playwright

from rpaquintoandar.infrastructure.config.settings_loader import BrowserSettings

logger = logging.getLogger(__name__)


class PlaywrightBrowserManager:
    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._set_local_browsers_path()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless,
            slow_mo=self._settings.slow_mo_ms,
        )
        logger.info(
            "Browser started (headless=%s, slow_mo=%dms)",
            self._settings.headless,
            self._settings.slow_mo_ms,
        )

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    @staticmethod
    def _set_local_browsers_path() -> None:
        if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
            local_path = Path(__file__).resolve().parents[4] / ".browsers"
            if local_path.exists():
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(local_path)
                logger.info("Using local browsers at %s", local_path)

    async def new_page(self) -> Page:
        assert self._browser is not None, "Browser not started"
        context = await self._browser.new_context(
            viewport={
                "width": self._settings.viewport_width,
                "height": self._settings.viewport_height,
            },
        )
        context.set_default_timeout(self._settings.timeout_ms)
        page = await context.new_page()
        return page
