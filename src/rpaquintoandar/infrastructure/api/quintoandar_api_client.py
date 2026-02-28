from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.infrastructure.api.response_parser import parse_search_response
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

PAGE_SIZE = 24


class QuintoAndarApiClient:
    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._settings.timeout_seconds),
                headers=DEFAULT_HEADERS,
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_body(self, criteria: SearchCriteria, offset: int) -> dict[str, Any]:
        filters: dict[str, Any] = {}

        if criteria.city:
            filters["city"] = criteria.city
        if criteria.state:
            filters["state"] = criteria.state
        if criteria.neighborhoods:
            filters["neighborhoods"] = criteria.neighborhoods
        if criteria.price_min is not None:
            filters["price_min"] = criteria.price_min
        if criteria.price_max is not None:
            filters["price_max"] = criteria.price_max
        if criteria.bedrooms_min is not None:
            filters["bedrooms_min"] = criteria.bedrooms_min
        if criteria.bedrooms_max is not None:
            filters["bedrooms_max"] = criteria.bedrooms_max
        if criteria.area_min is not None:
            filters["area_min"] = criteria.area_min
        if criteria.area_max is not None:
            filters["area_max"] = criteria.area_max

        return {
            "business_context": "SALE",
            "offset": offset,
            "size": PAGE_SIZE,
            "filters": filters,
        }

    async def search(
        self, criteria: SearchCriteria, offset: int = 0
    ) -> tuple[list[Listing], int]:
        client = await self._get_client()
        body = self._build_body(criteria, offset)

        logger.info("API search offset=%d city=%s", offset, criteria.city)
        response = await client.post(self._settings.search_url, json=body)
        response.raise_for_status()

        data = response.json()
        listings, total_count = parse_search_response(data)

        logger.info(
            "API response: %d listings, total=%d",
            len(listings),
            total_count,
        )

        if self._settings.delay_between_requests_ms > 0:
            await asyncio.sleep(self._settings.delay_between_requests_ms / 1000.0)

        return listings, total_count
