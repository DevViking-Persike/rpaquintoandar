from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rpaquintoandar.infrastructure.browser.page_objects.base_page import BasePage

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ListingDetailPage(BasePage):
    def __init__(self, page: Page, detail_base_url: str) -> None:
        super().__init__(page)
        self._detail_base_url = detail_base_url

    async def load_listing(self, listing_id: str) -> None:
        url = f"{self._detail_base_url}/{listing_id}"
        await self.navigate(url)
        await self._page.wait_for_load_state("domcontentloaded")

    async def extract_next_data(self) -> str:
        result = await self._page.evaluate(
            """
            () => {
                const el = document.querySelector('script#__NEXT_DATA__');
                return el ? el.textContent : '';
            }
            """
        )
        json_str = result or ""
        if json_str:
            logger.debug("Extracted __NEXT_DATA__ (%d chars)", len(json_str))
        else:
            logger.warning("__NEXT_DATA__ not found on page")
        return json_str
