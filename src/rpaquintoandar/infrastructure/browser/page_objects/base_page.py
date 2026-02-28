from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BasePage:
    def __init__(self, page: Page) -> None:
        self._page = page

    async def navigate(self, url: str) -> None:
        logger.debug("Navigating to %s", url)
        await self._page.goto(url, wait_until="domcontentloaded")

    async def close(self) -> None:
        await self._page.close()
