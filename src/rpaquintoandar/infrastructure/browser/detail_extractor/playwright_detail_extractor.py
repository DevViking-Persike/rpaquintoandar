from __future__ import annotations

import asyncio
import logging

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.interfaces import IBrowserManager
from rpaquintoandar.infrastructure.browser.page_objects.listing_detail_page import (
    ListingDetailPage,
)
from rpaquintoandar.infrastructure.config.settings_loader import ScrapingSettings

logger = logging.getLogger(__name__)


class PlaywrightDetailExtractor:
    def __init__(
        self,
        browser_manager: IBrowserManager,
        scraping_settings: ScrapingSettings,
    ) -> None:
        self._browser_manager = browser_manager
        self._settings = scraping_settings

    async def extract_detail(self, listing: Listing) -> str:
        attempts = self._settings.retry_attempts

        for attempt in range(1, attempts + 1):
            page = await self._browser_manager.new_page()
            detail_page = ListingDetailPage(page, self._settings.detail_base_url)
            try:
                await detail_page.load_listing(listing.source_id)
                json_str = await detail_page.extract_next_data()
                if json_str:
                    return json_str

                logger.warning(
                    "Empty __NEXT_DATA__ for %s (attempt %d/%d)",
                    listing.source_id,
                    attempt,
                    attempts,
                )
            except Exception:
                logger.exception(
                    "Error extracting detail for %s (attempt %d/%d)",
                    listing.source_id,
                    attempt,
                    attempts,
                )
            finally:
                await detail_page.close()

            if attempt < attempts:
                delay = self._settings.retry_delay_ms / 1000.0
                await asyncio.sleep(delay)

        return ""
