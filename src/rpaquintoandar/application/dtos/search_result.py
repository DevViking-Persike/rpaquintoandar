from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SearchResult:
    total_found: int = 0
    new_listings: int = 0
    pages_searched: int = 0
