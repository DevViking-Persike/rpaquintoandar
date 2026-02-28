from __future__ import annotations

import asyncio
import json
import logging
import unicodedata
from typing import Any

import httpx

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.interfaces import IBrowserManager
from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.infrastructure.api.response_parser import parse_ssr_houses
from rpaquintoandar.infrastructure.config.settings_loader import ApiSettings

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.quintoandar.com.br",
    "Referer": "https://www.quintoandar.com.br/",
}

COUNT_URL = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/count"
SEARCH_BASE_URL = "https://www.quintoandar.com.br/comprar/imovel"

PAGE_SIZE = 12


def _normalize_slug(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.lower().replace(" ", "-")


def _build_slug(criteria: SearchCriteria) -> str:
    city_slug = _normalize_slug(criteria.city)
    state_slug = criteria.state.lower()
    return f"{city_slug}-{state_slug}-brasil"


class QuintoAndarApiClient:
    def __init__(
        self,
        settings: ApiSettings,
        browser_manager: IBrowserManager | None = None,
    ) -> None:
        self._settings = settings
        self._browser_manager = browser_manager
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._settings.timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_count_body(self, criteria: SearchCriteria) -> dict[str, Any]:
        slug = _build_slug(criteria)

        houseSpecs: dict[str, Any] = {
            "area": {"range": {}},
            "houseTypes": [],
            "amenities": [],
            "installations": [],
            "bathrooms": {"range": {}},
            "bedrooms": {"range": {}},
            "parkingSpace": {"range": {}},
            "suites": {"range": {}},
        }

        if criteria.bedrooms_min is not None:
            houseSpecs["bedrooms"]["range"]["min"] = criteria.bedrooms_min
        if criteria.bedrooms_max is not None:
            houseSpecs["bedrooms"]["range"]["max"] = criteria.bedrooms_max
        if criteria.area_min is not None:
            houseSpecs["area"]["range"]["min"] = criteria.area_min
        if criteria.area_max is not None:
            houseSpecs["area"]["range"]["max"] = criteria.area_max

        price_range: list[dict[str, Any]] = []
        if criteria.price_min is not None or criteria.price_max is not None:
            pr: dict[str, Any] = {}
            if criteria.price_min is not None:
                pr["min"] = criteria.price_min
            if criteria.price_max is not None:
                pr["max"] = criteria.price_max
            price_range.append(pr)

        return {
            "context": {
                "mapShowing": True,
                "listShowing": True,
                "numPhotos": 12,
                "isSSR": False,
            },
            "filters": {
                "businessContext": "SALE",
                "blocklist": [],
                "selectedHouses": [],
                "location": {
                    "coordinate": {"lat": -23.55052, "lng": -46.633309},
                    "viewport": {},
                    "neighborhoods": criteria.neighborhoods or [],
                    "countryCode": "BR",
                },
                "priceRange": price_range,
                "specialConditions": [],
                "excludedSpecialConditions": [],
                "houseSpecs": houseSpecs,
                "availability": "ANY",
                "occupancy": "ANY",
                "partnerIds": [],
                "categories": [],
                "enableFlexibleSearch": True,
            },
            "pagination": {},
            "slug": slug,
            "fields": ["id"],
            "locationDescriptions": [{"description": slug}],
            "topics": [],
        }

    async def get_total_count(self, criteria: SearchCriteria) -> int:
        client = await self._get_client()
        body = self._build_count_body(criteria)

        response = await client.post(COUNT_URL, json=body, headers=DEFAULT_HEADERS)
        response.raise_for_status()

        data = response.json()
        total = data.get("hits", {}).get("total", {})
        count = total.get("value", 0) if isinstance(total, dict) else int(total or 0)
        logger.info("Total listings available: %d", count)
        return count

    async def search(
        self, criteria: SearchCriteria, offset: int = 0
    ) -> tuple[list[Listing], int]:
        slug = _build_slug(criteria)
        page_num = (offset // PAGE_SIZE) + 1

        url = f"{SEARCH_BASE_URL}/{slug}"
        if page_num > 1:
            url += f"?pagina={page_num}"

        logger.info("Playwright search page=%d slug=%s", page_num, slug)

        if self._browser_manager is None:
            raise RuntimeError("Browser manager required for search")

        page = await self._browser_manager.new_page()
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
            logger.warning("__NEXT_DATA__ not found in page (page=%d)", page_num)
            return [], 0

        listings, total_count = self._extract_from_json(json_str)

        logger.info(
            "Search response: %d listings, total=%d (page=%d)",
            len(listings),
            total_count,
            page_num,
        )

        if self._settings.delay_between_requests_ms > 0:
            await asyncio.sleep(self._settings.delay_between_requests_ms / 1000.0)

        return listings, total_count

    @staticmethod
    def _extract_from_json(json_str: str) -> tuple[list[Listing], int]:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse __NEXT_DATA__ JSON")
            return [], 0

        initial = data.get("props", {}).get("pageProps", {}).get("initialState", {})
        houses = initial.get("houses", {})

        listings = parse_ssr_houses(houses)

        # Try to get total count from search.markers
        search = initial.get("search", {})
        markers = search.get("markers", {})
        total = 0
        if isinstance(markers, dict):
            total_info = markers.get("total", {})
            if isinstance(total_info, dict):
                total = total_info.get("value", 0)
            elif isinstance(total_info, int):
                total = total_info

        return listings, total
