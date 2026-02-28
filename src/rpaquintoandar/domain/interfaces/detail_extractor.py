from __future__ import annotations

from typing import Protocol

from rpaquintoandar.domain.entities import Listing


class IDetailExtractor(Protocol):
    async def extract_detail(self, listing: Listing) -> str: ...
