from __future__ import annotations

import logging

from rpaquintoandar.application.dtos import SearchResult
from rpaquintoandar.domain.interfaces import IListingRepository, ISearchApiClient
from rpaquintoandar.domain.value_objects import SearchCriteria
from rpaquintoandar.infrastructure.api.quintoandar_api_client import PAGE_SIZE

logger = logging.getLogger(__name__)


class SearchListingsUseCase:
    def __init__(
        self,
        api_client: ISearchApiClient,
        listing_repo: IListingRepository,
        max_pages: int = 50,
    ) -> None:
        self._api_client = api_client
        self._repo = listing_repo
        self._max_pages = max_pages

    async def execute(self, criteria: SearchCriteria) -> SearchResult:
        logger.info("Searching listings: city=%s", criteria.city)
        result = SearchResult()

        offset = 0
        consecutive_no_new = 0
        max_consecutive_no_new = 3

        for page in range(1, self._max_pages + 1):
            listings, total_count = await self._api_client.search(criteria, offset)
            result.total_found = total_count
            result.pages_searched = page

            if not listings:
                logger.info("No more listings at offset %d, stopping", offset)
                break

            new_count = await self._repo.upsert_many(listings)
            result.new_listings += new_count

            logger.info(
                "Page %d: found=%d new=%d (total_available=%d)",
                page,
                len(listings),
                new_count,
                total_count,
            )

            if new_count == 0:
                consecutive_no_new += 1
                if consecutive_no_new >= max_consecutive_no_new:
                    logger.info(
                        "Stopping: %d consecutive pages with no new listings",
                        consecutive_no_new,
                    )
                    break
            else:
                consecutive_no_new = 0

            offset += PAGE_SIZE
            if total_count > 0 and offset >= total_count:
                logger.info("Reached end of results (offset=%d >= total=%d)", offset, total_count)
                break
            if len(listings) < PAGE_SIZE:
                logger.info("Last page (got %d < %d), stopping", len(listings), PAGE_SIZE)
                break

        logger.info(
            "Search completed: pages=%d total_found=%d new=%d",
            result.pages_searched,
            result.total_found,
            result.new_listings,
        )
        return result
