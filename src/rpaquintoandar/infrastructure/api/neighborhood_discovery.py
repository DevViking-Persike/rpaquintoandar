from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from rpaquintoandar.domain.interfaces import IBrowserManager
from rpaquintoandar.domain.value_objects import NeighborhoodInfo
from rpaquintoandar.infrastructure.config.settings_loader import ApiSettings

logger = logging.getLogger(__name__)

SEARCH_BASE_URL = "https://www.quintoandar.com.br/comprar/imovel"


class NeighborhoodDiscovery:
    def __init__(
        self,
        browser_manager: IBrowserManager,
        settings: ApiSettings,
    ) -> None:
        self._browser = browser_manager
        self._settings = settings

    async def discover(
        self,
        city_slug: str,
        property_type: str = "apartamento",
    ) -> list[NeighborhoodInfo]:
        """Discover neighborhoods by crawling QuintoAndar search pages.

        1. Visit city page, extract neighborhoods from __NEXT_DATA__ footer.
        2. For each discovered neighborhood, visit its page and discover more (1 level).
        3. Return unique list sorted by estimated_count desc.
        """
        seen_slugs: dict[str, NeighborhoodInfo] = {}

        # Level 0: city page
        seed_url = f"{SEARCH_BASE_URL}/{city_slug}/{property_type}"
        seed_neighborhoods = await self._extract_neighborhoods_from_page(seed_url)
        for n in seed_neighborhoods:
            seen_slugs[n.slug] = n

        logger.info(
            "Seed discovery: %d neighborhoods from city page", len(seen_slugs)
        )

        # Level 1: visit each discovered neighborhood page
        new_from_level1: list[NeighborhoodInfo] = []
        for info in list(seen_slugs.values()):
            nb_url = f"{SEARCH_BASE_URL}/{info.slug}/{property_type}"
            discovered = await self._extract_neighborhoods_from_page(nb_url)
            for n in discovered:
                if n.slug not in seen_slugs:
                    seen_slugs[n.slug] = n
                    new_from_level1.append(n)

        logger.info(
            "Level-1 discovery: +%d new neighborhoods (total: %d)",
            len(new_from_level1),
            len(seen_slugs),
        )

        result = sorted(
            seen_slugs.values(),
            key=lambda n: n.estimated_count,
            reverse=True,
        )
        return result

    async def _extract_neighborhoods_from_page(
        self, url: str
    ) -> list[NeighborhoodInfo]:
        """Navigate to a page and extract neighborhood info from __NEXT_DATA__."""
        page = await self._browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)

            json_str = await page.evaluate(
                """() => {
                    const el = document.querySelector('script#__NEXT_DATA__');
                    return el ? el.textContent : '';
                }"""
            )
        finally:
            await page.close()

        if not json_str:
            logger.warning("__NEXT_DATA__ not found at %s", url)
            return []

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse __NEXT_DATA__ JSON from %s", url)
            return []

        result = self._parse_neighborhoods(data)

        if self._settings.delay_between_requests_ms > 0:
            await asyncio.sleep(self._settings.delay_between_requests_ms / 1000.0)

        return result

    @staticmethod
    def _parse_neighborhoods(data: dict[str, Any]) -> list[NeighborhoodInfo]:
        """Extract neighborhoods from __NEXT_DATA__ structure."""
        initial = data.get("props", {}).get("pageProps", {}).get("initialState", {})
        search = initial.get("search", {})
        footer = search.get("footer", {})

        neighborhoods: dict[str, NeighborhoodInfo] = {}

        # Source 1: neighborhoodRecommendation (has count)
        recommendations = footer.get("neighborhoodRecommendation", [])
        if isinstance(recommendations, list):
            for rec in recommendations:
                slug = rec.get("slug", "")
                name = rec.get("name", "")
                count = rec.get("count", 0)
                if slug and name:
                    neighborhoods[slug] = NeighborhoodInfo(
                        name=name, slug=slug, estimated_count=count
                    )

        # Source 2: footerUrls.blocks → sublocation entries
        footer_urls = footer.get("footerUrls", {})
        blocks = footer_urls.get("blocks", [])
        if isinstance(blocks, list):
            for block in blocks:
                block_type = block.get("type", "")
                if block_type != "sublocation":
                    continue
                links = block.get("links", [])
                if isinstance(links, list):
                    for link in links:
                        slug = link.get("slug", "")
                        name = link.get("name", link.get("label", ""))
                        if slug and name and slug not in neighborhoods:
                            neighborhoods[slug] = NeighborhoodInfo(
                                name=name, slug=slug, estimated_count=0
                            )

        return list(neighborhoods.values())
