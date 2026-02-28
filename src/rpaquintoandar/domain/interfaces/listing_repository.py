from __future__ import annotations

from typing import Protocol

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.enums import ProcessingStatus
from rpaquintoandar.domain.value_objects import ContentHash


class IListingRepository(Protocol):
    async def upsert(self, listing: Listing) -> Listing: ...

    async def upsert_many(self, listings: list[Listing]) -> int: ...

    async def get_by_status(self, status: ProcessingStatus) -> list[Listing]: ...

    async def get_by_source_id(self, source_id: str) -> Listing | None: ...

    async def exists_by_hash(self, content_hash: ContentHash) -> bool: ...

    async def get_enriched(self) -> list[Listing]: ...
