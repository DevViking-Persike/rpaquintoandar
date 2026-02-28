from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from rpaquintoandar.domain.entities import Listing
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

SSR_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

COUNT_URL = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/count"
SEARCH_BASE_URL = "https://www.quintoandar.com.br/comprar/imovel"

PAGE_SIZE = 12


def _normalize_slug(text: str) -> str:
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.lower().replace(" ", "-")


def _build_slug(criteria: SearchCriteria) -> str:
    city_slug = _normalize_slug(criteria.city)
    state_slug = criteria.state.lower()
    return f"{city_slug}-{state_slug}-brasil"


class QuintoAndarApiClient:
    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
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
        client = await self._get_client()
        slug = _build_slug(criteria)
        page_num = (offset // PAGE_SIZE) + 1

        url = f"{SEARCH_BASE_URL}/{slug}"
        params: dict[str, Any] = {}
        if page_num > 1:
            params["pagina"] = page_num

        logger.info("SSR search page=%d slug=%s", page_num, slug)
        response = await client.get(url, params=params, headers=SSR_HEADERS)
        response.raise_for_status()

        html = response.text
        listings, total_count = self._extract_from_ssr(html)

        logger.info(
            "SSR response: %d listings, total=%d (page=%d)",
            len(listings),
            total_count,
            page_num,
        )

        if self._settings.delay_between_requests_ms > 0:
            await asyncio.sleep(self._settings.delay_between_requests_ms / 1000.0)

        return listings, total_count

    @staticmethod
    def _extract_from_ssr(html: str) -> tuple[list[Listing], int]:
        marker = '<script id="__NEXT_DATA__" type="application/json">'
        start = html.find(marker)
        if start == -1:
            logger.warning("__NEXT_DATA__ not found in SSR response")
            return [], 0

        start += len(marker)
        end = html.find("</script>", start)
        if end == -1:
            return [], 0

        json_str = html[start:end]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse __NEXT_DATA__ JSON")
            return [], 0

        initial = data.get("props", {}).get("pageProps", {}).get("initialState", {})
        houses = initial.get("houses", {})

        listings = parse_ssr_houses(houses)

        # Try to get total count from search.markers or count endpoint
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
