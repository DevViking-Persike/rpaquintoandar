from __future__ import annotations

import pytest

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import ProcessingStatus
from rpaquintoandar.domain.value_objects import Address, ContentHash, PriceInfo
from rpaquintoandar.infrastructure.persistence.database_manager import DatabaseManager
from rpaquintoandar.infrastructure.persistence.sqlite_listing_repo import SqliteListingRepo


def make_listing(source_id: str = "test-1", **kwargs) -> Listing:
    defaults = {
        "source_id": source_id,
        "source_url": f"https://www.quintoandar.com.br/imovel/{source_id}",
    }
    defaults.update(kwargs)
    return Listing(**defaults)


@pytest.mark.asyncio
async def test_upsert_and_get_by_source_id(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listing = make_listing("upsert-1")

    result = await repo.upsert(listing)
    assert result.id is not None

    fetched = await repo.get_by_source_id("upsert-1")
    assert fetched is not None
    assert fetched.source_id == "upsert-1"


@pytest.mark.asyncio
async def test_upsert_updates_existing(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listing = make_listing("update-1")
    await repo.upsert(listing)

    listing.description = "Updated description"
    await repo.upsert(listing)

    fetched = await repo.get_by_source_id("update-1")
    assert fetched is not None
    assert fetched.description == "Updated description"


@pytest.mark.asyncio
async def test_upsert_many(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listings = [make_listing(f"many-{i}") for i in range(5)]

    created = await repo.upsert_many(listings)
    assert created == 5

    created = await repo.upsert_many(listings)
    assert created == 0


@pytest.mark.asyncio
async def test_get_by_status(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listing = make_listing("status-1")
    await repo.upsert(listing)

    pending = await repo.get_by_status(ProcessingStatus.PENDING)
    assert any(l.source_id == "status-1" for l in pending)


@pytest.mark.asyncio
async def test_exists_by_hash(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listing = make_listing("hash-1")
    content_hash = ContentHash.from_text("test content for hashing")

    listing.mark_enriched(content_hash)
    await repo.upsert(listing)

    assert await repo.exists_by_hash(content_hash) is True
    assert await repo.exists_by_hash(ContentHash.from_text("other")) is False


@pytest.mark.asyncio
async def test_get_enriched(db_manager: DatabaseManager):
    repo = SqliteListingRepo(db_manager)
    listing = make_listing("enriched-1")
    listing.mark_enriched(ContentHash.from_text("content"))
    await repo.upsert(listing)

    enriched = await repo.get_enriched()
    assert any(l.source_id == "enriched-1" for l in enriched)
