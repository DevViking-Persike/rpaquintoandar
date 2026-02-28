from __future__ import annotations

import logging
from typing import Any

from rpaquintoandar.application.dtos import SearchResult
from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.interfaces import IListingRepository, ISearchApiClient
from rpaquintoandar.domain.value_objects import Coordinates, SearchCriteria
from rpaquintoandar.infrastructure.api.coordinates_collector import CoordinatesCollector

logger = logging.getLogger(__name__)

DETAIL_BASE_URL = "https://www.quintoandar.com.br/imovel"


class SegmentedSearchUseCase:
    """Collect listing IDs in bulk using the coordinates API.

    Strategy:
    1. Load a search page in Playwright to trigger the coordinates API
    2. Intercept the response to get up to 10,000 listing IDs
    3. Create minimal PENDING listings in the database
    4. The pipeline's ExtractStep then enriches each via detail pages
    """

    def __init__(
        self,
        api_client: ISearchApiClient,
        listing_repo: IListingRepository,
        coordinates_collector: CoordinatesCollector,
        max_pages_per_segment: int = 50,
    ) -> None:
        self._api_client = api_client
        self._repo = listing_repo
        self._collector = coordinates_collector
        self._max_pages_per_segment = max_pages_per_segment

    async def execute(
        self,
        criteria: SearchCriteria,
        target_count: int = 1000,
        price_ranges: list[dict[str, Any]] | None = None,
        property_type: str = "apartamento",
    ) -> SearchResult:
        from rpaquintoandar.infrastructure.api.quintoandar_api_client import (
            _build_slug,
        )

        city_slug = _build_slug(criteria)

        logger.info(
            "SegmentedSearch: collecting IDs via coordinates API "
            "(target=%d, slug=%s, type=%s)",
            target_count,
            city_slug,
            property_type,
        )

        # Phase 1: Collect listing IDs via coordinates API
        id_tuples = await self._collector.collect_ids(
            city_slug=city_slug,
            property_type=property_type,
            target_count=target_count,
        )

        if not id_tuples:
            logger.warning("No listing IDs collected from coordinates API")
            return SearchResult()

        # Phase 2: Create minimal PENDING listings and save to DB
        listings = []
        for source_id, lat, lon in id_tuples:
            listing = Listing(
                source_id=source_id,
                source_url=f"{DETAIL_BASE_URL}/{source_id}",
            )
            if lat and lon:
                listing.coordinates = Coordinates(latitude=lat, longitude=lon)
            listings.append(listing)

        new_count = await self._repo.upsert_many(listings)

        logger.info(
            "SegmentedSearch completed: %d IDs collected, %d new listings saved",
            len(id_tuples),
            new_count,
        )

        result = SearchResult()
        result.total_found = len(id_tuples)
        result.new_listings = new_count
        return result
