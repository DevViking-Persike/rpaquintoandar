from __future__ import annotations

from typing import Protocol

from rpaquintoandar.domain.entities import Listing
from rpaquintoandar.domain.value_objects import SearchCriteria


class ISearchApiClient(Protocol):
    async def search(
        self, criteria: SearchCriteria, offset: int = 0
    ) -> tuple[list[Listing], int]: ...
