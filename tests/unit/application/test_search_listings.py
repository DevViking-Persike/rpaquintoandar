from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from rpaquintoandar.application.use_cases import SearchListingsUseCase
from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.value_objects import SearchCriteria


@pytest.mark.asyncio
async def test_search_listings_returns_result():
    listings = [
        Listing(
            source_id="listing-1",
            source_url="https://www.quintoandar.com.br/imovel/listing-1",
        ),
    ]

    api_client = AsyncMock()
    api_client.search = AsyncMock(return_value=(listings, 1))

    repo = AsyncMock()
    repo.upsert_many = AsyncMock(return_value=1)

    use_case = SearchListingsUseCase(api_client, repo, max_pages=1)
    result = await use_case.execute(SearchCriteria())

    assert result.total_found == 1
    assert result.new_listings == 1
    api_client.search.assert_awaited_once()
    repo.upsert_many.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_listings_no_results():
    api_client = AsyncMock()
    api_client.search = AsyncMock(return_value=([], 0))

    repo = AsyncMock()

    use_case = SearchListingsUseCase(api_client, repo, max_pages=1)
    result = await use_case.execute(SearchCriteria())

    assert result.total_found == 0
    assert result.new_listings == 0
